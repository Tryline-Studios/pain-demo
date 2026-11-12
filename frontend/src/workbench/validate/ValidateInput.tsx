import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Validation } from "@/workbench/validate/useValidation";

/** The left pane in Validate mode: drop or pick a file, or paste XML (spec 17.9). */
export function ValidateInput({ validation }: { validation: Validation }) {
  const [pasted, setPasted] = useState("");

  return (
    <div className="flex flex-col gap-4">
      <header className="px-1 pb-2">
        <h1 className="font-semibold text-xl tracking-tight">Validate a pain.001 message</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Checked against the XSD of the Message Version it declares (.03 to .13).
        </p>
      </header>
      <textarea
        aria-label="Paste XML"
        value={pasted}
        onChange={(event) => setPasted(event.target.value)}
        placeholder="…or paste XML"
        spellCheck={false}
        className="h-48 rounded-xl border bg-card p-3 font-mono text-xs"
      />
      <Button disabled={pasted === "" || validation.isPending} onClick={() => validation.validateXml(pasted)}>
        Validate pasted XML
      </Button>
    </div>
  );
}
