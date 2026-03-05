export function StorySkeleton() {
  return (
    <div className="space-y-5 px-1" aria-label="加载中">
      {[0.65, 0.9, 0.78, 0.55, 0.85, 0.42].map((width, i) => (
        <div
          key={i}
          className="skeleton-line"
          style={{ width: `${width * 100}%`, animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  )
}
