import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Validation } from "@/workbench/validate/useValidation";

/** The left pane in Validate mode: drop or pick a file, or paste XML (spec 17.9). */
export function ValidateInput({ validation }: { validation: Validation }) {
  const [pasted, setPasted] = useState("");
  const [over, setOver] = useState(false);

  const validateFirst = (files: FileList | null) => {
    const file = files?.[0];
    if (file !== undefined) {
      validation.validateFile(file);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <header className="px-1 pb-2">
        <h1 className="font-semibold text-xl tracking-tight">Validate a pain.001 message</h1>
        <p className="mt-1 text-muted-foreground text-sm">
          Checked against the XSD of the Message Version it declares (.03 to .13).
        </p>
      </header>
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setOver(false);
          validateFirst(event.dataTransfer.files);
        }}
        className={cn(
          "block cursor-pointer rounded-xl border-2 border-dashed p-8 text-center focus-within:ring-2 focus-within:ring-ring",
          { "border-primary bg-accent": over },
        )}
      >
        <input
          type="file"
          accept=".xml,application/xml,text/xml"
          className="sr-only"
          onChange={(event) => {
            validateFirst(event.target.files);
            // Picking the same file again should validate it again.
            event.target.value = "";
          }}
        />
        <span className="block font-medium">Drop a pain.001 file here</span>
        <span className="mt-1 block text-muted-foreground text-sm">or click to choose one (.xml, up to 10 MB)</span>
      </label>
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
