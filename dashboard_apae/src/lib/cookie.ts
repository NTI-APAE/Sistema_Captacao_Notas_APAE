export function parseSessionCookie(header: string, expectedName: string) {
  const first = header.split(";", 1)[0];
  const separator = first.indexOf("=");
  if (separator < 1 || first.slice(0, separator) !== expectedName) return null;
  const value = first.slice(separator + 1);
  if (!value || value.length > 200) return null;
  return value;
}
