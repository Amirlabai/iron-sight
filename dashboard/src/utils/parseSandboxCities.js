/** Split sandbox city input on semicolons or newlines. */
export function parseSandboxCities(input) {
  if (!input?.trim()) return [];
  return input.split(/[;\n]/).map((c) => c.trim()).filter(Boolean);
}
