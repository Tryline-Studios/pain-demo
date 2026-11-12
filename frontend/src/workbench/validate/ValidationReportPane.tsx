/** The right pane in Validate mode: the Validation Report, or its empty state before the first validation. */
export function ValidationReportPane() {
  return (
    <div className="flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-dashed text-center">
      <p className="font-medium text-lg">No message validated yet</p>
    </div>
  );
}
