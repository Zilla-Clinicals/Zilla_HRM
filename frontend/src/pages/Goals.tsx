import { GoalsPanel } from "../components/GoalsPanel";

export function MyGoals() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">My Goals</h1>
        <p className="text-sm text-slate-500">
          Set goals for the year, check in on your progress, and close them out
        </p>
      </div>
      <GoalsPanel mine canEdit heading="Goals" />
    </div>
  );
}
