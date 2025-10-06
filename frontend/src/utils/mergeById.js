function mergeById(a, b) {
  const m = new Map(a.map(x => [x.id, x]));
  for (const x of b) m.set(x.id, x);
  return [...m.values()];
}

export default mergeById;