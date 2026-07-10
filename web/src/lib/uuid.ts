/**
 * Thin wrapper around the native crypto.randomUUID() (available in all
 * modern browsers and Node 19+) - no uuid package needed for a single
 * client-side ID generator. Named v4 to match the common "uuidv4" call
 * site convention without adding a dependency.
 */
export function v4(): string {
  return crypto.randomUUID();
}
