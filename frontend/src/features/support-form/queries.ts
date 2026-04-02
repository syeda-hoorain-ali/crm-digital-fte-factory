import type { SupportFormValues, SupportFormResponse } from "@/features/support-form/schema"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080"

export class SupportApiError extends Error {
  public status: number
  public details?: unknown

  constructor(
    message: string,
    status: number,
    details?: unknown
  ) {
    super(message)
    this.status = status
    this.details = details
    this.name = "SupportApiError"
  }
}

export async function supportRequestQuery(
  data: SupportFormValues
): Promise<SupportFormResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/support/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new SupportApiError(
        errorData.detail || "Failed to submit support request",
        response.status,
        errorData
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof SupportApiError) {
      throw error
    }
    throw new SupportApiError(
      "Network error. Please check your connection and try again.",
      0
    )
  }
}

export async function getTicketStatusQuery(ticketId: string): Promise<{
  ticket_id: string
  status: string
  created_at: string
  messages: Array<{
    content: string
    role: string
    created_at: string
  }>
}> {
  try {
    const response = await fetch(`${API_BASE_URL}/support/ticket/${ticketId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new SupportApiError(
        errorData.detail || "Failed to fetch ticket status",
        response.status,
        errorData
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof SupportApiError) {
      throw error
    }
    throw new SupportApiError(
      "Network error. Please check your connection and try again.",
      0
    )
  }
}
