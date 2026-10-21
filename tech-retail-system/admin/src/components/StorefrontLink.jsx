import React from "react";
import { ArrowUpRight } from "lucide-react";
import useRemote from "../../../shared/useRemote";

export default function StorefrontLink() {
  const { data } = useRemote("features/");
  let href = "";
  try {
    const url = new URL(data?.customer_frontend_url);
    if (
      ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password &&
      !url.search &&
      !url.hash
    )
      href = url.href;
  } catch {
    /* Wait for a valid configured storefront URL. */
  }
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer">
      Mở cửa hàng <ArrowUpRight size={14} />
    </a>
  ) : (
    <button type="button" disabled title="Chưa tải được địa chỉ cửa hàng">
      Mở cửa hàng <ArrowUpRight size={14} />
    </button>
  );
}
