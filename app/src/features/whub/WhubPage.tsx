import { TodoWidget } from './TodoWidget';

export function WhubPage() {
  return (
    <div className="whub-overview">
      <div className="whub-overview-grid">
        <div className="whub-overview-todo">
          <TodoWidget />
        </div>
      </div>
    </div>
  );
}
