import type { ParameterField } from "@/types/resource";

export interface TestParamValue {
  name: string;
  value: string;
}

function defaultValueForType(type: ParameterField["type"]): unknown {
  if (type === "number") return 0;
  if (type === "boolean") return false;
  return "";
}

function coerceParamValue(type: ParameterField["type"] | "string", raw: string): unknown {
  if (type === "number") {
    const parsed = Number(raw);
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  if (type === "boolean") {
    return raw === "true" || raw === "1";
  }
  return raw;
}

function savedValueForParameter(param: ParameterField): unknown {
  if (param.default_value?.trim()) {
    return coerceParamValue(param.type, param.default_value);
  }
  return defaultValueForType(param.type);
}

export function buildTestPayload(
  parameters: ParameterField[],
  paramValues: TestParamValue[],
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  const typeByName = Object.fromEntries(
    parameters.filter((p) => p.name.trim()).map((p) => [p.name, p.type]),
  );

  for (const param of parameters) {
    if (!param.name.trim()) continue;
    payload[param.name] = savedValueForParameter(param);
  }

  for (const entry of paramValues) {
    if (!entry.name.trim() || !entry.value.trim()) continue;
    const paramType = typeByName[entry.name] ?? "string";
    payload[entry.name] = coerceParamValue(paramType, entry.value);
  }

  return payload;
}

