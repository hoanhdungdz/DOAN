import imageIndex from "./product-image-index.json";
import overrides from "./product-image-overrides.json";

export function imageSources(source) {
  return [
    ...new Set(
      [
        imageIndex[source],
        overrides[source]?.url || source,
        "/placeholder.svg",
      ].filter(Boolean),
    ),
  ];
}

export function imageNote(source) {
  return overrides[source]?.note || "";
}
