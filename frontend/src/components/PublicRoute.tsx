import { Navigate, Outlet } from "react-router-dom";
import { isAuthenticated } from "../api";

export const PublicRoute = () => {
  if (isAuthenticated()) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};
