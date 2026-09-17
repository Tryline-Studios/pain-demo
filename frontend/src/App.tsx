import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Workbench } from "@/workbench/Workbench";

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Workbench />
    </QueryClientProvider>
  );
}
