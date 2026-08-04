import { useEffect, useState } from "react";
import { fetchBlob } from "../lib/apiClient";
import { IconUser } from "./icons";

/**
 * Shows an employee's profile photo (fetched with auth) or a person-icon fallback.
 * `className` controls size/shape/background of the container.
 * Bump `refreshKey` to force a re-fetch after an upload/removal.
 */
export function PhotoAvatar({
  employeeId,
  hasPhoto,
  className = "",
  iconClassName = "h-1/2 w-1/2 text-brand-500",
  refreshKey = 0,
}: {
  employeeId: number;
  hasPhoto: boolean;
  className?: string;
  iconClassName?: string;
  refreshKey?: number;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    if (hasPhoto) {
      fetchBlob(`/api/employees/${employeeId}/photo`).then((blob) => {
        if (cancelled || !blob) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      });
    } else {
      setUrl(null);
    }
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [employeeId, hasPhoto, refreshKey]);

  return (
    <div className={`grid place-items-center overflow-hidden ${className}`}>
      {url ? (
        <img src={url} alt="" className="h-full w-full object-cover" />
      ) : (
        <IconUser className={iconClassName} />
      )}
    </div>
  );
}
