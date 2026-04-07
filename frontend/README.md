# CloudStream CRM - Frontend

**🌐 Live Demo**: [https://cloudstream-crm.vercel.app/](https://cloudstream-crm.vercel.app/)

## Overview

This is the frontend application for CloudStream CRM's Customer Success Digital FTE system. It provides a web-based support form for customers to submit support requests.

## Features

- **Support Form**: Complete React component with validation
  - Name, email, subject, category, and message fields
  - Priority selection (low, medium, high)
  - Category selection (general, technical, billing, bug_report, feedback)
  - Real-time validation
  - Success/error state handling
  - Ticket ID generation and display

- **Responsive Design**: Mobile-first design using Tailwind CSS
- **Modern UI**: Built with shadcn/ui components
- **Type Safety**: Full TypeScript implementation

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: shadcn/ui + Tailwind CSS
- **Forms**: react-hook-form + zod validation
- **HTTP Client**: Axios
- **Routing**: React Router

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── support-form.tsx      # Main support form component
│   │   └── ui/                   # shadcn/ui components
│   ├── features/
│   │   └── support-form/         # Support form feature module
│   │       ├── hooks.ts          # Custom hooks
│   │       ├── queries.ts        # API queries
│   │       └── schema.ts         # Zod validation schemas
│   ├── pages/
│   │   ├── index.tsx             # Home page with support form
│   │   └── not-found.tsx         # 404 page
│   ├── App.tsx                   # Main app component
│   └── main.tsx                  # Entry point
├── public/
│   └── favicon.ico
└── package.json
```

## API Integration

The support form submits to the backend API endpoint:

```typescript
POST /api/support/submit
Content-Type: application/json

{
  "name": "Customer Name",
  "email": "customer@example.com",
  "subject": "Support Request",
  "category": "technical",
  "priority": "medium",
  "message": "Description of the issue..."
}
```

Response:
```typescript
{
  "ticket_id": "uuid",
  "message": "Thank you for contacting us!",
  "estimated_response_time": "Usually within 5 minutes"
}
```

## Deployment

The frontend is deployed to Vercel at [https://cloudstream-crm.vercel.app/](https://cloudstream-crm.vercel.app/)

### Automatic Deployment
- Push to `main` branch triggers automatic deployment
- Pull requests get preview URLs

### Environment Variables
Configure in Vercel dashboard:
```bash
VITE_API_URL=https://your-api-endpoint.com
```

## Component Documentation

### SupportForm

The main support form component with full validation and state management.

**Features**:
- Form validation using zod schema
- Real-time error display
- Loading states during submission
- Success state with ticket ID display
- Error handling with user-friendly messages

**Usage**:
```tsx
import { SupportForm } from '@/components/support-form';

function Page() {
  return <SupportForm />;
}
```

