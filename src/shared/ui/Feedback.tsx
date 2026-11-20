import { CircleAlert, LoaderCircle } from "lucide-react";

export function ErrorMessage({ message }: { readonly message: string }) {
    return (
        <p className="error-message" role="alert">
            <CircleAlert size={17} aria-hidden />
            {message}
        </p>
    );
}

export function Spinner({ size = 18 }: { readonly size?: number }) {
    return <LoaderCircle className="spinner" size={size} aria-hidden />;
}
