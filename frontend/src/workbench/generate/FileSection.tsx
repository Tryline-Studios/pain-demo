import type { ReactNode } from "react";
import type { components } from "@/api/schema";
import { cn } from "@/lib/utils";
import type { GenerationRequest } from "@/workbench/generate/useGeneration";

type Options = components["schemas"]["Options"];
type MessageVersionOption = components["schemas"]["MessageVersionOption"];
type Country = components["schemas"]["SupportedCountry"];
type ExposureCountry = components["schemas"]["ExposureCountry"];
type MessageVersion = components["schemas"]["MessageVersion"];

/** What the File section's fields hold; text fields stay text so the API, not the form, judges them. */
export type FileSettings = {
  message_version: MessageVersion;
  transaction_count: string;
  seed: string;
  countries: Country[];
  currencies: string[];
  amount_min: string;
  amount_max: string;
  exposure_countries: ExposureCountry[];
  exposure_count: string;
};

export function defaultFileSettings(options: Options): FileSettings {
  const { defaults } = options;
  return {
    message_version: defaults.message_version,
    transaction_count: String(defaults.transaction_count),
    seed: "",
    countries: defaults.countries,
    currencies: [],
    amount_min: defaults.amount_min,
    amount_max: defaults.amount_max,
    exposure_countries: defaults.exposure_countries,
    exposure_count: "0",
  };
}

/**
 * The request body: only the fields the user changed, so the API's defaults apply to the rest. A cleared Seed or no
 * currency chips are left out too, so the API picks them (spec 5.1).
 */
export function generationRequest(changed: Partial<FileSettings>): Partial<GenerationRequest> {
  const { transaction_count, seed, currencies, exposure_count, ...rest } = changed;
  return {
    ...rest,
    ...(transaction_count === undefined ? {} : { transaction_count: Number(transaction_count) }),
    ...(exposure_count === undefined ? {} : { exposure_count: Number(exposure_count) }),
    ...(seed ? { seed } : {}),
    ...(currencies?.length ? { currencies } : {}),
  };
}

function toggle<T>(list: T[], item: T) {
  return list.includes(item) ? list.filter((x) => x !== item) : [...list, item];
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    // biome-ignore lint/a11y/noLabelWithoutControl: the control is the child
    <label className="flex flex-col gap-1.5">
      <span className={LABEL}>{label}</span>
      {children}
    </label>
  );
}

function Chips<T extends string>({
  label,
  all,
  chosen,
  onToggle,
}: {
  label: string;
  all: T[];
  chosen: T[];
  onToggle: (item: T) => void;
}) {
  return (
    // biome-ignore lint/a11y/useSemanticElements: a row of pressed-state toggles, not a form fieldset
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {all.map((item) => (
        <button
          key={item}
          type="button"
          aria-pressed={chosen.includes(item)}
          onClick={() => onToggle(item)}
          className={cn(
            "h-[26px] rounded-full border bg-secondary px-2.5 font-medium text-xs tabular-nums focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1",
            {
              "border-primary bg-primary text-primary-foreground": chosen.includes(item),
            },
          )}
        >
          {item}
        </button>
      ))}
    </div>
  );
}

export const LABEL = "font-medium text-label text-xs";
export const INPUT =
  "h-9 w-full rounded-md border border-border-strong bg-card px-2.5 font-mono text-sm focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-1 aria-invalid:border-destructive";

/**
 * Message Version, transactions, Seed, countries, amount range, currencies, exposure countries and count, all from
 * the API (spec 13.2).
 */
export function FileSection({
  options,
  messageVersions,
  value,
  onChange,
}: {
  options: Options;
  messageVersions: MessageVersionOption[];
  value: FileSettings;
  onChange: (patch: Partial<FileSettings>) => void;
}) {
  const set = onChange;
  const currencies = [...new Set(options.countries.map((c) => c.currency))];

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Message Version">
          <select
            className={INPUT}
            value={value.message_version}
            onChange={(e) => set({ message_version: e.target.value as MessageVersion })}
          >
            {messageVersions.map((v) => (
              <option key={v.message_version} value={v.message_version}>
                {v.message_version}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Transactions">
          <input
            type="number"
            className={INPUT}
            min={1}
            max={options.limits.max_transactions}
            value={value.transaction_count}
            onChange={(e) => set({ transaction_count: e.target.value })}
          />
        </Field>
      </div>
      <Field label="Seed">
        <input
          type="text"
          className={INPUT}
          maxLength={options.limits.max_seed_length}
          placeholder="Empty: the app picks one and echoes it"
          value={value.seed}
          onChange={(e) => set({ seed: e.target.value })}
        />
      </Field>
      <div className="flex flex-col gap-2 text-xs">
        <span className={LABEL}>Countries</span>
        <Chips
          label="Countries"
          all={options.countries.map((c) => c.country)}
          chosen={value.countries}
          onToggle={(country) => set({ countries: toggle(value.countries, country) })}
        />
        <div className="flex flex-wrap items-center gap-2 text-muted-foreground">
          <span>Debtor country: {value.countries[0] ?? "none"}</span>
          {value.countries.slice(1).map((country) => (
            <button
              key={country}
              type="button"
              onClick={() => set({ countries: [country, ...value.countries.filter((c) => c !== country)] })}
              className="rounded-full border border-dashed px-2 text-primary hover:text-foreground"
            >
              Make {country} Debtor
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Minimum amount">
          <input
            type="text"
            inputMode="decimal"
            className={INPUT}
            value={value.amount_min}
            onChange={(e) => set({ amount_min: e.target.value })}
          />
        </Field>
        <Field label="Maximum amount">
          <input
            type="text"
            inputMode="decimal"
            className={INPUT}
            value={value.amount_max}
            onChange={(e) => set({ amount_max: e.target.value })}
          />
        </Field>
      </div>
      <div className="flex flex-col gap-2 text-xs">
        <span className={LABEL}>Currencies</span>
        <Chips
          label="Currencies"
          all={currencies}
          chosen={value.currencies}
          onToggle={(currency) => set({ currencies: toggle(value.currencies, currency) })}
        />
        <span className="text-muted-foreground">None chosen: each creditor is paid in its country's currency.</span>
      </div>
      <div className="flex flex-col gap-2 text-xs">
        <span className={LABEL}>Exposure countries</span>
        <Chips
          label="Exposure countries"
          all={options.exposure_countries.map((c) => c.country)}
          chosen={value.exposure_countries}
          onToggle={(country) => set({ exposure_countries: toggle(value.exposure_countries, country) })}
        />
        <span className="text-muted-foreground">
          Each Exposure moves a clean transaction's creditor, agent, account and currency into one of them.
        </span>
      </div>
      <Field label="Exposures">
        <input
          type="number"
          className={INPUT}
          min={0}
          max={options.limits.max_transactions}
          value={value.exposure_count}
          onChange={(e) => set({ exposure_count: e.target.value })}
        />
      </Field>
    </>
  );
}
