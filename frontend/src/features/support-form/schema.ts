import { z } from "zod"

export const MAX_MESSAGE_LENGTH = 1000;

export const supportFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "Name must be at least 2 characters.")
    .max(100, "Name must be less than 100 characters."),

  email: z
    .email("Please enter a valid email address.")
    .trim()
    .max(255, "Email must be less than 255 characters."),

  phone: z.string().trim().max(30, "Phone number is too long.").optional().or(z.literal("")),

  subject: z
    .string()
    .trim()
    .min(3, "Subject must be at least 3 characters.")
    .max(200, "Subject must be less than 200 characters."),

  category: z.enum(
    ["general", "technical", "billing", "feedback", "bug_report"],
    "Please select a valid category."
  ),

  priority: z.enum(
    ["low", "medium", "high", "critical"],
    "Please select a valid priority level."
  ),

  message: z
    .string()
    .trim()
    .min(10, "Message must be at least 10 characters.")
    .max(MAX_MESSAGE_LENGTH, `Message must be less than ${MAX_MESSAGE_LENGTH} characters.`),
})

export type SupportFormValues = z.infer<typeof supportFormSchema>

export interface SupportFormResponse {
  ticket_id: string
  message: string
  estimated_response_time: string
}
