import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../shared/types";
import { useAuth } from "./useAuth";
import { LoadingSpinner } from "../components/LoadingSpinner";

interface Props {
  children: React.ReactNode;
  roles?: Role[];
}

export function ProtectedRoute({ children, roles }: Props) {
  const { me, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingSpinner full />;
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(me.user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
