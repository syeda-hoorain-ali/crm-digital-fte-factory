import toast from "react-hot-toast";
import { useMutation } from "@tanstack/react-query";
import type { SupportFormValues } from "./schema";
import { getTicketStatusQuery, SupportApiError, supportRequestQuery } from "./queries";

export const useSupportForm = () => {
  // const queryClient = useQueryClient();

  const submitSupportRequest = useMutation({
    mutationFn: async (data: SupportFormValues) => {
      return supportRequestQuery(data)
    },
    onError: (error) => {
      if (error instanceof SupportApiError) {
        toast.error(error.message)
      } else {
        toast.error("Something went wrong. Please try again.")
      }
    },
    onSuccess: async () => {
      toast.success(
        "Your message has been sent! We'll get back to you soon.",
        { duration: 5000 }
      );
    },
  });

  const getTicketStatus = useMutation({
    mutationFn: async (ticketId: string) => {
      return getTicketStatusQuery(ticketId)
    },
    onError: (error) => {
      toast.error(error.message);
    },
    onSuccess: async () => {
      toast.success("Project added successfully");
    },
  });


  return { submitSupportRequest, getTicketStatus };
};
