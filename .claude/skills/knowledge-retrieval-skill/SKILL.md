---
name: knowledge-retrieval-skill
description: Retrieve relevant product documentation and knowledge base articles using semantic search. Use this whenever a customer asks product-related questions, "how-to" guides, or technical specs. This skill leverages the search_knowledge_base tool from the crm-digital-fte MCP server.
---

# Knowledge Retrieval Skill

## Purpose
This skill enables retrieval of relevant product documentation and knowledge base articles to answer customer questions about products, features, and technical specifications. It uses semantic search to find the most relevant information.

## When to Use This Skill
- Customer asks product-related questions
- Customer requests "how-to" guides or tutorials
- Customer asks about technical specifications
- Customer inquires about product features or capabilities
- Need to provide documentation to support customer queries

## Execution Path
To fulfill this skill, invoke the `search_knowledge_base` tool from the `crm-digital-fte` MCP server.

## Inputs
- `query`: (Required) The search query string containing the customer's question or topic
- `max_results`: (Optional) Maximum number of results to return (default: 5, min: 1, max: 20)

## Expected Output
The skill returns a formatted response containing:
- Document titles that match the query
- Relevance/similarity scores for each result
- Content snippets from relevant documents
- Category information for context

## Execution Steps
1. Formulate a precise search query based on the customer's question
2. Call the `search_knowledge_base` tool with the query
3. Analyze the results returned by the tool
4. Extract and summarize the most relevant information
5. Format the response appropriately for the customer

## Guardrails
- **NEVER fabricate or make up information** - only use content from the search results
- If the MCP tool returns no results, inform the customer that relevant documentation wasn't found
- If search results indicate the knowledge base is unavailable, inform the customer of the temporary issue
- If unable to find relevant information, consider suggesting the "Escalation Decision Skill"
- Always cite information sources from the knowledge base when providing answers
- Maintain factual accuracy and attribute responses to documented sources

## Examples
- Customer: "How do I set up payment processing?"
  - Use: `search_knowledge_base(query="payment processing setup", max_results=5)`
- Customer: "What are the API rate limits?"
  - Use: `search_knowledge_base(query="API rate limits", max_results=3)`
- Customer: "How to integrate with your webhook system?"
  - Use: `search_knowledge_base(query="webhook integration guide", max_results=5)`

## Error Handling
- If search returns "Knowledge base temporarily unavailable", inform customer and suggest escalation if urgent
- If search returns no relevant results, acknowledge this limitation and consider escalation
- If search fails entirely, inform customer of the technical issue and suggest alternative support channels
