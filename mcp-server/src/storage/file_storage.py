"""File-based storage implementations for tickets, knowledge base, replies, and customers."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class TicketStorage:
    """Manages ticket data in JSON file."""

    def __init__(self, tickets_file: str):
        self.tickets_file = Path(tickets_file)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create tickets file if it doesn't exist."""
        if not self.tickets_file.exists():
            self.tickets_file.parent.mkdir(parents=True, exist_ok=True)
            self.tickets_file.write_text("[]")

    def load_tickets(self) -> List[Dict]:
        """Load all tickets from JSON file."""
        try:
            with open(self.tickets_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse {self.tickets_file}")
            return []

    def save_tickets(self, tickets: List[Dict]):
        """Save tickets to JSON file."""
        with open(self.tickets_file, "w") as f:
            json.dump(tickets, f, indent=4)

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict]:
        """Get a specific ticket by ID."""
        tickets = self.load_tickets()
        for ticket in tickets:
            if ticket.get("id") == ticket_id:
                return ticket
        return None

    def create_ticket(self, ticket_data: Dict) -> str:
        """Create a new ticket and return its ID."""
        tickets = self.load_tickets()

        # Generate next ticket ID
        existing_ids = [t.get("id", "") for t in tickets]
        ticket_numbers = []
        for tid in existing_ids:
            match = re.match(r"TKT-(\d+)", tid)
            if match:
                ticket_numbers.append(int(match.group(1)))

        next_number = max(ticket_numbers, default=0) + 1
        new_id = f"TKT-{next_number:03d}"

        # Add ticket with generated ID
        ticket_data["id"] = new_id
        if "created_at" not in ticket_data:
            ticket_data["created_at"] = datetime.now().isoformat()
        if "status" not in ticket_data:
            ticket_data["status"] = "open"

        tickets.append(ticket_data)
        self.save_tickets(tickets)

        return new_id

    def update_ticket(self, ticket_id: str, updates: Dict) -> bool:
        """Update an existing ticket."""
        tickets = self.load_tickets()

        for i, ticket in enumerate(tickets):
            if ticket.get("id") == ticket_id:
                tickets[i].update(updates)
                tickets[i]["updated_at"] = datetime.now().isoformat()
                self.save_tickets(tickets)
                return True

        return False

    def get_customer_tickets(self, email: Optional[str] = None, phone: Optional[str] = None) -> List[Dict]:
        """Get all tickets for a customer by email or phone."""
        tickets = self.load_tickets()
        customer_tickets = []

        for ticket in tickets:
            if email and ticket.get("customer_email") == email:
                customer_tickets.append(ticket)
            elif phone and ticket.get("customer_phone") == phone:
                customer_tickets.append(ticket)

        return customer_tickets


class KnowledgeBaseStorage:
    """Manages knowledge base documents with TF-IDF search."""

    def __init__(self, context_dir: str):
        self.context_dir = Path(context_dir)
        self.documents = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self._load_documents()

    def _load_documents(self):
        """Load all markdown documents from context directory."""
        self.documents = []

        if not self.context_dir.exists():
            logger.warning(f"Context directory not found: {self.context_dir}")
            return

        for md_file in self.context_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")

                # Split into sections by headers
                sections = self._split_into_sections(content, md_file.name)
                self.documents.extend(sections)

            except Exception as e:
                logger.error(f"Failed to load {md_file}: {e}")

        # Build TF-IDF index
        if self.documents:
            self._build_tfidf_index()

    def _split_into_sections(self, content: str, filename: str) -> List[Dict]:
        """Split markdown content into searchable sections."""
        sections = []
        lines = content.split("\n")
        current_section = {"title": filename, "content": "", "source": filename}

        for line in lines:
            # Check for headers
            if line.startswith("#"):
                # Save previous section if it has content
                if current_section["content"].strip():
                    sections.append(current_section.copy())

                # Start new section
                title = line.lstrip("#").strip()
                current_section = {
                    "title": title,
                    "content": line + "\n",
                    "source": filename
                }
            else:
                current_section["content"] += line + "\n"

        # Add last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _build_tfidf_index(self):
        """Build TF-IDF index for all documents."""
        corpus = [doc["content"] for doc in self.documents]
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words="english",
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search documents using TF-IDF similarity."""
        if not self.documents or self.vectorizer is None:
            return []

        # Transform query
        query_vector = self.vectorizer.transform([query])

        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # Get top K results
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Only return results with some similarity
                results.append({
                    "title": self.documents[idx]["title"],
                    "content": self.documents[idx]["content"].strip(),
                    "source": self.documents[idx]["source"],
                    "similarity_score": float(similarities[idx])
                })

        return results

    def load_all_documents(self) -> List[Dict]:
        """Return all loaded documents."""
        return self.documents


class ReplyStorage:
    """Manages reply files in the replies directory."""

    def __init__(self, replies_dir: str):
        self.replies_dir = Path(replies_dir)
        self.replies_dir.mkdir(parents=True, exist_ok=True)

    def save_reply(self, ticket_id: str, content: str, channel: str, customer: str = "unknown"):
        """Save a reply to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reply_{ticket_id}_{timestamp}.txt"
        filepath = self.replies_dir / filename

        # Format reply content
        reply_content = f"""Ticket ID: {ticket_id}
Customer: {customer}
Channel: {channel}
Timestamp: {datetime.now().isoformat()}
Reply:
{content}
"""

        filepath.write_text(reply_content, encoding="utf-8")
        logger.info(f"Reply saved to {filepath}")

    def get_replies_for_ticket(self, ticket_id: str) -> List[str]:
        """Get all replies for a specific ticket."""
        replies = []
        pattern = f"reply_{ticket_id}_*.txt"

        for reply_file in self.replies_dir.glob(pattern):
            try:
                content = reply_file.read_text(encoding="utf-8")
                replies.append(content)
            except Exception as e:
                logger.error(f"Failed to read {reply_file}: {e}")

        return replies


class CustomerStorage:
    """Manages customer data extracted from tickets."""

    def __init__(self, ticket_storage: TicketStorage):
        self.ticket_storage = ticket_storage

    def get_customer_by_contact(self, email: Optional[str] = None, phone: Optional[str] = None) -> Optional[Dict]:
        """Get customer information by email or phone."""
        tickets = self.ticket_storage.load_tickets()

        for ticket in tickets:
            if email and ticket.get("customer_email") == email:
                return {
                    "email": ticket.get("customer_email"),
                    "phone": ticket.get("customer_phone"),
                    "found_in_ticket": ticket.get("id")
                }
            elif phone and ticket.get("customer_phone") == phone:
                return {
                    "email": ticket.get("customer_email"),
                    "phone": ticket.get("customer_phone"),
                    "found_in_ticket": ticket.get("id")
                }

        return None

    def get_customer_history(self, email: Optional[str] = None, phone: Optional[str] = None) -> Dict:
        """Get customer information and their ticket history."""
        customer = self.get_customer_by_contact(email, phone)

        if not customer:
            return {
                "customer": None,
                "tickets": [],
                "total_tickets": 0
            }

        tickets = self.ticket_storage.get_customer_tickets(
            email=customer.get("email"),
            phone=customer.get("phone")
        )

        return {
            "customer": customer,
            "tickets": tickets,
            "total_tickets": len(tickets)
        }

    def create_or_get_customer(self, email: Optional[str] = None, phone: Optional[str] = None) -> Dict:
        """Create or retrieve customer information."""
        customer = self.get_customer_by_contact(email, phone)

        if customer:
            return customer

        # For file-based storage, customers are implicitly created with tickets
        return {
            "email": email,
            "phone": phone,
            "found_in_ticket": None
        }
