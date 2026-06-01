import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function StepNavigator({
  steps,
  currentIndex,
  onIndexChange,
}) {
  if (!steps?.length) {
    return (
      <div className="step-navigator empty">
        <p className="muted">Select an archive event to load replay steps.</p>
      </div>
    );
  }

  const atStart = currentIndex <= 0;
  const atEnd = currentIndex >= steps.length - 1;

  return (
    <div className="step-navigator">
      <div className="nav-controls">
        <button
          type="button"
          disabled={atStart}
          onClick={() => onIndexChange(currentIndex - 1)}
          aria-label="Previous step"
        >
          <ChevronLeft size={18} />
          Prev
        </button>
        <span className="step-counter">
          {currentIndex + 1} / {steps.length}
        </span>
        <button
          type="button"
          disabled={atEnd}
          onClick={() => onIndexChange(currentIndex + 1)}
          aria-label="Next step"
        >
          Next
          <ChevronRight size={18} />
        </button>
      </div>
      <ol className="step-list">
        {steps.map((step, i) => (
          <li key={step.id}>
            <button
              type="button"
              className={i === currentIndex ? 'active' : ''}
              onClick={() => onIndexChange(i)}
            >
              <span className="step-id">{step.id}</span>
              <span className="step-title">{step.title}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
