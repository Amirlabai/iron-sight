/** Keep ref.current in sync with latest state/props during render. */
export function useSyncRefs(pairs) {
  for (let i = 0; i < pairs.length; i += 1) {
    const [ref, value] = pairs[i];
    ref.current = value;
  }
}
