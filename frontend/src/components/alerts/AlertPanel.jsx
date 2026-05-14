"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  Chip,
  Input,
  Label,
  Modal,
  TextArea,
  useOverlayState,
} from "@heroui/react";
import { Danger, SecuritySafe, TickCircle } from "../../icons/isax.jsx";
import { useDashboard } from "../../context/DashboardContext.jsx";
import { formatApiError } from "../../services/api.js";
import TransactionGraph, { useAlertGraph } from "../graph/TransactionGraph.jsx";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

function patternLabel(p) {
  const u = (p || "").toUpperCase().replace(/_/g, " ");
  return u || "FRAUD PATTERN";
}

export default function AlertPanel() {
  const { activeAlert, alerts, releaseAlert, escalateAlert, setActiveAlert } = useDashboard();
  const [flash, setFlash] = useState(false);
  const [modal, setModal] = useState(null);
  const [analystName, setAnalystName] = useState("");
  const [reason, setReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);

  const dialog = useOverlayState({
    isOpen: Boolean(modal),
    onOpenChange: useCallback(
      (open) => {
        if (!open && !actionLoading) {
          setModal(null);
          setActionError(null);
          setAnalystName("");
          setReason("");
        }
      },
      [actionLoading]
    ),
  });

  const graphData = useAlertGraph(activeAlert?.transaction_ref);
  const resolved = Boolean(activeAlert?.resolved_at);
  const isHold = activeAlert?.alert_level >= 3;

  useEffect(() => {
    if (activeAlert?.alert_level >= 3) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 520);
      return () => clearTimeout(t);
    }
    return undefined;
  }, [activeAlert?.id, activeAlert?.alert_level]);

  const history = useMemo(() => (Array.isArray(alerts) ? alerts.slice(0, 10) : []), [alerts]);

  async function submitAction() {
    if (!modal || !analystName.trim()) return;
    const id = modal.id;
    const body = { analyst_name: analystName.trim(), release_reason: reason.trim() };
    setActionLoading(true);
    setActionError(null);
    try {
      if (modal.kind === "release") await releaseAlert(id, body);
      else await escalateAlert(id, body);
      setModal(null);
      setAnalystName("");
      setReason("");
    } catch (e) {
      const msg = formatApiError(e);
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="relative flex h-full min-h-0 flex-col">
      {flash ? (
        <div
          className="pointer-events-none fixed inset-0 z-50 border-[3px] border-danger/55 shadow-[inset_0_0_80px_rgba(255,60,60,0.12)]"
          aria-hidden
        />
      ) : null}

      <Card.Root className="flex min-h-0 flex-1 flex-col rounded-2xl border border-default-200/80 bg-content1/85 shadow-md backdrop-blur-md">
        <Card.Content className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 sm:p-5">
          {!activeAlert ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 py-16 text-center">
              <TickCircle size={48} variant="Bold" className="text-success" />
              <p className="text-success text-xs font-bold uppercase tracking-[0.2em]">All clear</p>
              <p className="text-default-500 max-w-md text-sm leading-relaxed">
                No active monitored cases in queue. Live monitoring continues across inbound transfers.
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {resolved ? (
                <Chip color="success" variant="flat" className="w-fit font-semibold uppercase">
                  Resolved · {(activeAlert.action_taken || "").toUpperCase()}
                  {activeAlert.resolved_at ? ` · ${activeAlert.resolved_at}` : ""}
                </Chip>
              ) : null}

              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-widest">Risk score</p>
                  <p className="from-danger to-warning bg-gradient-to-br bg-clip-text text-4xl font-extrabold tracking-tight text-transparent sm:text-5xl">
                    {(Number(activeAlert.risk_score || 0) * 100).toFixed(0)}%
                  </p>
                  <p className="text-default-500 mt-1 text-xs">
                    Level {activeAlert.alert_level}
                    {activeAlert.alert_level === 2 ? " · Monitored" : activeAlert.alert_level >= 3 ? " · Hold" : ""}
                  </p>
                </div>
                <Chip color="danger" variant="bordered" className="max-w-[200px] font-bold uppercase leading-snug">
                  {patternLabel(activeAlert.pattern_type)}
                </Chip>
              </div>

              <Card.Root variant="bordered" className="rounded-xl border-default-200/80 bg-content2/30">
                <Card.Content className="p-4">
                  <p className="text-default-600 text-sm leading-relaxed">{activeAlert.reason}</p>
                </Card.Content>
              </Card.Root>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Card.Root variant="bordered" className="rounded-xl border-default-200/60">
                  <Card.Content className="gap-1 p-4">
                    <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Sender</p>
                    <p className="text-default-foreground font-mono text-sm">{activeAlert.sender_account}</p>
                    <p className="text-default-500 text-xs">{activeAlert.sender_bank}</p>
                  </Card.Content>
                </Card.Root>
                <Card.Root variant="bordered" className="rounded-xl border-default-200/60">
                  <Card.Content className="gap-1 p-4">
                    <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Amount</p>
                    <p className="text-default-foreground text-lg font-bold">
                      {fmt.format(activeAlert.amount_naira ?? activeAlert.transaction?.amount_naira ?? 0)}
                    </p>
                    <p className="text-default-500 font-mono text-xs">{activeAlert.created_at}</p>
                  </Card.Content>
                </Card.Root>
              </div>

              {isHold ? (
                <Card.Root className="rounded-xl border border-success/30 bg-success/10">
                  <Card.Content className="gap-2 p-4">
                    <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Squad API status</p>
                    <div className="text-success flex gap-2 text-sm leading-relaxed">
                      <SecuritySafe size={20} variant="Bold" className="mt-0.5 shrink-0" />
                      <span>Pre-settlement hold applied (simulated core-banking hold after engine decision).</span>
                    </div>
                  </Card.Content>
                </Card.Root>
              ) : (
                <Card.Root className="rounded-xl border border-warning/30 bg-warning/10">
                  <Card.Content className="p-4">
                    <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Monitoring</p>
                    <p className="text-warning text-sm leading-relaxed">
                      Elevated risk (L2). No simulated core-banking hold — review and escalate if needed.
                    </p>
                  </Card.Content>
                </Card.Root>
              )}

              <div className="flex flex-wrap gap-2">
                <Button
                  color="warning"
                  variant="flat"
                  className="flex-1 min-w-[140px] font-semibold"
                  isDisabled={resolved || actionLoading}
                  onPress={() => {
                    setActionError(null);
                    setModal({ kind: "release", id: activeAlert.id });
                  }}
                >
                  Release hold
                </Button>
                <Button
                  color="danger"
                  variant="solid"
                  className="flex-1 min-w-[140px] font-semibold"
                  isDisabled={resolved || actionLoading}
                  onPress={() => {
                    setActionError(null);
                    setModal({ kind: "escalate", id: activeAlert.id });
                  }}
                >
                  Escalate
                </Button>
              </div>

              <TransactionGraph graphData={graphData} />
            </div>
          )}

          <div>
            <p className="text-default-500 mb-2 text-[0.65rem] font-bold uppercase tracking-widest">Alert history</p>
            <div className="flex flex-col gap-2">
              {history.map((a) => (
                <Button
                  key={a.id}
                  variant="bordered"
                  className="h-auto justify-start border-default-200/80 bg-content2/30 py-3 text-left"
                  onPress={() => setActiveAlert(a)}
                >
                  <div className="w-full">
                    <div className="flex justify-between gap-2">
                      <span className="text-danger font-mono text-sm font-bold">{(Number(a.risk_score || 0) * 100).toFixed(0)}%</span>
                      <span className="text-default-500 text-[0.65rem] font-semibold uppercase tracking-wide">{a.pattern_type}</span>
                    </div>
                    <p className="text-default-foreground mt-1 text-sm font-semibold">
                      {fmt.format(a.amount_naira ?? a.transaction?.amount_naira ?? 0)}
                    </p>
                    <p className="text-default-500 mt-1 text-xs uppercase">{(a.action_taken || "").toUpperCase()}</p>
                  </div>
                </Button>
              ))}
            </div>
          </div>
        </Card.Content>
      </Card.Root>

      <Modal.Root state={dialog}>
        <Modal.Backdrop isDismissable={!actionLoading} />
        <Modal.Container size="md" placement="center">
          <Modal.Dialog>
            <Modal.Header>
              <Modal.Heading className="text-default-foreground flex items-center gap-2 text-lg font-bold">
                <Danger size={22} variant="Bold" className="text-danger" />
                {modal?.kind === "release" ? "Release hold" : modal?.kind === "escalate" ? "Escalate case" : "Action"}
              </Modal.Heading>
            </Modal.Header>
            <Modal.Body className="gap-4">
              {actionError ? (
                <p className="text-danger text-sm" role="alert">
                  {actionError}
                </p>
              ) : null}
              <div className="flex flex-col gap-2">
                <Label className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Analyst name</Label>
                <Input value={analystName} onChange={(e) => setAnalystName(e.target.value)} isDisabled={actionLoading} autoFocus />
              </div>
              <div className="flex flex-col gap-2">
                <Label className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Reason</Label>
                <TextArea value={reason} onChange={(e) => setReason(e.target.value)} isDisabled={actionLoading} rows={3} />
              </div>
            </Modal.Body>
            <Modal.Footer className="flex justify-end gap-2">
              <Button variant="bordered" isDisabled={actionLoading} onPress={() => dialog.close()}>
                Cancel
              </Button>
              <Button color="warning" isDisabled={actionLoading || !analystName.trim()} onPress={() => submitAction()}>
                {actionLoading ? "Working…" : "Confirm"}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Root>
    </div>
  );
}
