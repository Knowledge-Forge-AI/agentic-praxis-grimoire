// APG74-FX-001: ordinary .ts under the exact TypeScript 7 CLI checker.
// Exercises structural assignability, satisfies, exhaustive narrowing, and
// the noUncheckedIndexedAccess=true consequence declared in tsconfig.json.

export type Tier = "free" | "pro" | "enterprise";

export interface SeatPolicy {
  readonly tier: Tier;
  readonly seats: number;
}

const DEFAULT_POLICIES = {
  free: { tier: "free", seats: 3 },
  pro: { tier: "pro", seats: 50 },
} satisfies Record<string, SeatPolicy>;

export function describePolicy(policy: SeatPolicy): string {
  switch (policy.tier) {
    case "free":
    case "pro":
    case "enterprise":
      return `${policy.tier}:${policy.seats}`;
    default: {
      const unreachable: never = policy.tier;
      return unreachable;
    }
  }
}

export function lookupPolicy(name: string): SeatPolicy | undefined {
  const table: Record<string, SeatPolicy> = DEFAULT_POLICIES;
  return table[name];
}
