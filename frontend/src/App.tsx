import { Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { AcceptInvite } from "./pages/AcceptInvite";
import { Analytics } from "./pages/Analytics";
import { AuditLog } from "./pages/AuditLog";
import { Dashboard } from "./pages/Dashboard";
import { DoReview } from "./pages/DoReview";
import { DoSelfAssessment } from "./pages/DoSelfAssessment";
import { Employees } from "./pages/Employees";
import { EmployeeProfile } from "./pages/EmployeeProfile";
import { GoalDetail } from "./pages/GoalDetail";
import { MyGoals } from "./pages/Goals";
import { ForgotPassword } from "./pages/ForgotPassword";
import { Kpis } from "./pages/Kpis";
import { Login } from "./pages/Login";
import { MyReviews } from "./pages/MyReviews";
import { ResetPassword } from "./pages/ResetPassword";
import { ReviewCycles } from "./pages/ReviewCycles";
import { SecuritySettings } from "./pages/SecuritySettings";
import { SelfAssessment } from "./pages/SelfAssessment";
import { DoSurvey } from "./pages/DoSurvey";
import { Surveys } from "./pages/Surveys";
import { SurveyManage } from "./pages/SurveyManage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/accept-invite" element={<AcceptInvite />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/self-assessment" element={<SelfAssessment />} />
        <Route path="/self-assessment/:assignmentId" element={<DoSelfAssessment />} />
        <Route path="/goals" element={<MyGoals />} />
        <Route path="/goals/:goalId" element={<GoalDetail />} />
        <Route path="/surveys" element={<Surveys />} />
        <Route path="/surveys/:id/fill" element={<DoSurvey />} />
        <Route
          path="/surveys/:id/manage"
          element={
            <ProtectedRoute roles={["manager", "hr", "executive", "admin"]}>
              <SurveyManage />
            </ProtectedRoute>
          }
        />
        <Route path="/employees" element={<Employees />} />
        <Route path="/employees/:id" element={<EmployeeProfile />} />
        <Route path="/settings" element={<SecuritySettings />} />
        <Route
          path="/reviews"
          element={
            <ProtectedRoute roles={["manager", "hr", "executive", "admin"]}>
              <MyReviews />
            </ProtectedRoute>
          }
        />
        <Route
          path="/reviews/:assignmentId"
          element={
            <ProtectedRoute roles={["manager", "hr", "executive", "admin"]}>
              <DoReview />
            </ProtectedRoute>
          }
        />
        <Route
          path="/kpis"
          element={
            <ProtectedRoute roles={["hr", "executive", "admin"]}>
              <Kpis />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cycles"
          element={
            <ProtectedRoute roles={["hr", "executive", "admin"]}>
              <ReviewCycles />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute roles={["hr", "executive", "admin"]}>
              <Analytics />
            </ProtectedRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <ProtectedRoute roles={["hr", "executive", "admin"]}>
              <AuditLog />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="*" element={<Login />} />
    </Routes>
  );
}
