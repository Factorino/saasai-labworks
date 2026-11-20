import { API_BASE_URL } from "@/shared/config";

export class HttpError extends Error {
    constructor(
        readonly status: number,
        readonly code: string | undefined,
        readonly entity: string | undefined,
    ) {
        super(`HTTP ${status}`);
        this.name = "HttpError";
    }
}

function readProperty(value: unknown, key: string): unknown {
    return value && typeof value === "object" && key in value
        ? (value as Record<string, unknown>)[key]
        : undefined;
}

function readString(value: unknown, key: string): string | undefined {
    const property = readProperty(value, key);
    return typeof property === "string" ? property : undefined;
}

export async function request(path: string, options: RequestInit, format: "empty"): Promise<void>;
export async function request<T>(path: string, options: RequestInit): Promise<T>;
export async function request(
    path: string,
    options: RequestInit,
    format?: "empty",
): Promise<unknown> {
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");
    if (options.body !== undefined) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
        cache: "no-store",
        credentials: "omit",
    });
    if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        throw new HttpError(
            response.status,
            readString(body, "code"),
            readString(readProperty(body, "detail"), "entity"),
        );
    }
    if (format === "empty") {
        if (response.status !== 204) {
            throw new HttpError(response.status, undefined, undefined);
        }
        return;
    }
    return response.json();
}
