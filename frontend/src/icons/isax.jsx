import { forwardRef } from "react";
import {
  Activity as ActivityRaw,
  ArrowLeft2 as ArrowLeft2Raw,
  ArrowRight2 as ArrowRight2Raw,
  Chart2 as Chart2Raw,
  Danger as DangerRaw,
  Flash as FlashRaw,
  Home2 as Home2Raw,
  Notification as NotificationRaw,
  Radar2 as Radar2Raw,
  SecuritySafe as SecuritySafeRaw,
  TickCircle as TickCircleRaw,
  WalletMoney as WalletMoneyRaw,
} from "iconsax-react";

/**
 * iconsax-react sets defaults via defaultProps on forwardRef components. In React 19 those
 * defaults may not run, so stroke/fill get `undefined` and icons render blank. This wrapper
 * applies the same defaults with plain parameter defaults.
 */
function wrapIcon(Raw, defaultSize = 24) {
  const Comp = forwardRef(function IsaxIcon(props, ref) {
    const { color = "currentColor", variant = "Linear", size = defaultSize, ...rest } = props;
    return <Raw ref={ref} color={color} variant={variant} size={size} {...rest} />;
  });
  Comp.displayName = Raw.displayName || Raw.name || "IsaxIcon";
  return Comp;
}

export const Activity = wrapIcon(ActivityRaw);
export const ArrowLeft2 = wrapIcon(ArrowLeft2Raw);
export const ArrowRight2 = wrapIcon(ArrowRight2Raw);
export const Chart2 = wrapIcon(Chart2Raw);
export const Danger = wrapIcon(DangerRaw);
export const Flash = wrapIcon(FlashRaw);
export const Home2 = wrapIcon(Home2Raw);
export const Notification = wrapIcon(NotificationRaw);
export const Radar2 = wrapIcon(Radar2Raw);
export const SecuritySafe = wrapIcon(SecuritySafeRaw);
export const TickCircle = wrapIcon(TickCircleRaw);
export const WalletMoney = wrapIcon(WalletMoneyRaw);
