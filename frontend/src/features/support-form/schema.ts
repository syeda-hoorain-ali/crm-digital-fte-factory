import { z } from "zod"

export const supportFormSchema = z.object({
  name: z.string().min(2, {
    message: "Name must be at least 2 characters.",
  }),
  email: z.string().email({
    message: "Please enter a valid email address.",
  }),
  subject: z.string().min(5, {
    message: "Subject must be at least 5 characters.",
  }),
  category: z.enum(["general", "technical", "billing", "feedback", "bug_report"], {
    required_error: "Please select a category.",
  }),
  priority: z.enum(["low", "medium", "high", "critical"], {
    required_error: "Please select a priority level.",
  }),
  message: z.string().min(10, {
    message: "Message must be at least 10 characters.",
  }),
})

export type SupportFormValues = z.infer<typeof supportFormSchema>

export interface SupportFormResponse {
  ticket_id: string
  message: string
  estimated_response_time: string
}
