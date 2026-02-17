interface Step {
  title: string;
  status?: 'done' | 'in_progress' | 'pending';
}

interface ImplementationPlanProps {
  planJson: string;
  currentStep: number;
}

export default function ImplementationPlan({
  planJson,
  currentStep,
}: ImplementationPlanProps) {
  let steps: Step[] = [];
  try {
    const parsed: unknown = JSON.parse(planJson);
    if (Array.isArray(parsed)) {
      steps = parsed.map((item: unknown, index: number) => {
        if (typeof item === 'string') {
          return {
            title: item,
            status:
              index < currentStep
                ? 'done' as const
                : index === currentStep
                  ? 'in_progress' as const
                  : 'pending' as const,
          };
        }
        const obj = item as Record<string, unknown>;
        return {
          title: (obj.title as string) || `Step ${index + 1}`,
          status:
            (obj.status as Step['status']) ||
            (index < currentStep
              ? 'done'
              : index === currentStep
                ? 'in_progress'
                : 'pending'),
        };
      });
    }
  } catch {
    // Invalid JSON, show nothing
  }

  if (steps.length === 0) {
    return (
      <p className="text-gray-500 text-sm">No implementation plan defined.</p>
    );
  }

  const icons: Record<string, string> = {
    done: '\u2705',
    in_progress: '\uD83D\uDD04',
    pending: '\u2B1C',
  };

  return (
    <div className="space-y-2">
      {steps.map((step, i) => (
        <div
          key={i}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 ${
            step.status === 'in_progress'
              ? 'bg-blue-900/30 border border-blue-700'
              : 'bg-gray-800/50'
          }`}
        >
          <span className="text-lg">{icons[step.status ?? 'pending']}</span>
          <span
            className={`text-sm ${
              step.status === 'done'
                ? 'text-gray-400 line-through'
                : step.status === 'in_progress'
                  ? 'text-white font-medium'
                  : 'text-gray-500'
            }`}
          >
            {i + 1}. {step.title}
          </span>
          {step.status === 'in_progress' && (
            <span className="ml-auto text-xs text-blue-400">current</span>
          )}
        </div>
      ))}
    </div>
  );
}
