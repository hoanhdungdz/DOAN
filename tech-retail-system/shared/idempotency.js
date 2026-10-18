export function operationKey(cache, operation, payload) {
  const fingerprint = operation + JSON.stringify(payload);
  if (!cache.has(fingerprint)) cache.set(fingerprint, crypto.randomUUID());
  return cache.get(fingerprint);
}
