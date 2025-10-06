function mergeById(existing, incoming) {
  const map = new Map(existing.map(p => [p.id, p]));
  for (const p of incoming) map.set(p.id, p);
  return Array.from(map.values());
}

export default mergeById;