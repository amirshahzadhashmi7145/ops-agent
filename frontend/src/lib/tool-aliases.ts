/** Keep in sync with backend ALIAS_NAMES (generic names for multi-company SOPs). */
export const ALIAS_TOOL_NAMES = new Set([
  "lookup_account",
  "list_customer_assets",
  "lookup_asset",
  "get_asset_health",
  "get_order_status",
]);

export function isAliasTool(name: string, flag?: boolean): boolean {
  if (typeof flag === "boolean") return flag;
  return ALIAS_TOOL_NAMES.has(name);
}
