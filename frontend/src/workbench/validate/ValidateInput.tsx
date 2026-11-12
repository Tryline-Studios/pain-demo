import { Upload } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { PRIMARY_BUTTON } from "@/workbench/OutputPane";
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
      <h2 className="font-semibold text-[11px] text-muted-foreground uppercase tracking-[0.08em]">Message</h2>
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
          "flex cursor-pointer flex-wrap items-center gap-4 rounded-[10px] border border-border-strong border-dashed bg-card px-[18px] py-4 focus-within:outline-2 focus-within:outline-ring focus-within:outline-offset-2",
          { "border-primary bg-primary-soft": over },
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
        <span className="flex size-10 flex-none items-center justify-center rounded-lg bg-primary-soft text-primary">
          <Upload className="size-5" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold">Drop a pain.001 file here</span>
          <span className="block text-[12.5px] text-muted-foreground">
            XML up to 10 MB · Message Versions .03 to .13
          </span>
        </span>
        {/* The whole zone is the file input's label, so this is its look, not a second control. */}
        <span className="inline-flex h-9 items-center rounded-md border border-border-strong bg-card px-3.5 font-medium hover:bg-secondary">
          Choose file
        </span>
      </label>
      <textarea
        aria-label="Paste XML"
        value={pasted}
        onChange={(event) => setPasted(event.target.value)}
        placeholder="…or paste XML"
        spellCheck={false}
        className="h-48 rounded-[10px] border border-border-strong bg-card p-3 font-mono text-xs focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1"
      />
      <Button
        className={PRIMARY_BUTTON}
        disabled={pasted === "" || validation.isPending}
        onClick={() => validation.validateXml(pasted)}
      >
        Validate pasted XML
      </Button>
    </div>
  );
}
