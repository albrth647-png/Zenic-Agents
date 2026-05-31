// AG-UI Protocol — Agent-Generated UI Components
// React components that render dynamically based on agent specifications

"use client";

import React from "react";
import type {
  AGUIComponent,
  AGUIFormField,
  AGUIChartData,
  AGUITableColumn,
  AGUIMetricCard as AGUIMetricCardType,
  AGUIApprovalEvent,
} from "@/lib/ag-ui/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

// ─── Risk Badge ──────────────────────────────────────────────

function RiskBadge({ level }: { level: string }) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    low: "secondary",
    medium: "default",
    high: "destructive",
    critical: "destructive",
  };
  return <Badge variant={variants[level] || "default"}>{level.toUpperCase()}</Badge>;
}

// ─── Form Renderer ───────────────────────────────────────────

function AgentForm({ props: formProps }: { props: Record<string, unknown> }) {
  const fields = (formProps.fields || []) as AGUIFormField[];

  return (
    <div className="space-y-4">
      {fields.map((field) => (
        <div key={field.name} className="space-y-2">
          <Label htmlFor={field.name}>
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          {field.type === "textarea" ? (
            <Textarea
              id={field.name}
              placeholder={field.placeholder}
              defaultValue={field.defaultValue as string ?? ""}
            />
          ) : field.type === "select" ? (
            <Select>
              <SelectTrigger>
                <SelectValue placeholder={field.placeholder || "Select..."} />
              </SelectTrigger>
              <SelectContent>
                {(field.options || []).map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              id={field.name}
              type={field.type}
              placeholder={field.placeholder}
              defaultValue={field.defaultValue as string ?? ""}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Table Renderer ──────────────────────────────────────────

function AgentTable({ props: tableProps }: { props: Record<string, unknown> }) {
  const columns = (tableProps.columns || []) as AGUITableColumn[];
  const rows = (tableProps.rows || []) as Record<string, unknown>[];

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={col.key} style={col.width ? { width: col.width } : undefined}>
              {col.label}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => (
          <TableRow key={i}>
            {columns.map((col) => (
              <TableCell key={col.key}>{String(row[col.key] ?? "")}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ─── Chart Placeholder ───────────────────────────────────────

function AgentChart({ props: chartProps }: { props: Record<string, unknown> }) {
  const data = chartProps as AGUIChartData;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{data.title || "Chart"}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center h-48 bg-muted rounded-md">
          <p className="text-muted-foreground text-sm">
            {data.type?.toUpperCase() || "BAR"} Chart — {data.datasets?.length || 0} dataset(s), {data.labels?.length || 0} labels
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Metric Card ─────────────────────────────────────────────

function AgentMetricCard({ props: metricProps }: { props: Record<string, unknown> }) {
  const data = metricProps as AGUIMetricCardType;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{data.title}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{data.value}</div>
        {data.change !== undefined && (
          <p className={`text-xs mt-1 ${data.change >= 0 ? "text-green-600" : "text-red-600"}`}>
            {data.change >= 0 ? "+" : ""}{data.change}% {data.changeLabel || ""}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Approval Card ───────────────────────────────────────────

function AgentApprovalCard({ props: approvalProps }: { props: Record<string, unknown> }) {
  const data = approvalProps as AGUIApprovalEvent;
  return (
    <Card className="border-orange-500/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Approval Required</CardTitle>
          <RiskBadge level={data.riskLevel || "medium"} />
        </div>
        {data.policyViolation && (
          <CardDescription className="text-orange-600">{data.policyViolation}</CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <p className="text-sm">{data.suggestedAction || "Please review and approve or reject this action."}</p>
      </CardContent>
      <CardFooter className="gap-2">
        <Button variant="destructive" size="sm">Reject</Button>
        <Button size="sm">Approve</Button>
      </CardFooter>
    </Card>
  );
}

// ─── Main Renderer ───────────────────────────────────────────

export function AGUIRenderer({ components }: { components: AGUIComponent[] }) {
  return (
    <div className="ag-ui-container space-y-4">
      {components.map((comp) => {
        switch (comp.type) {
          case "form":
            return (
              <Card key={comp.id}>
                {comp.title && <CardHeader><CardTitle>{comp.title}</CardTitle></CardHeader>}
                <CardContent><AgentForm props={comp.props} /></CardContent>
              </Card>
            );
          case "table":
            return (
              <Card key={comp.id}>
                {comp.title && <CardHeader><CardTitle>{comp.title}</CardTitle></CardHeader>}
                <CardContent><AgentTable props={comp.props} /></CardContent>
              </Card>
            );
          case "chart":
            return <AgentChart key={comp.id} props={comp.props} />;
          case "metric-card":
            return <AgentMetricCard key={comp.id} props={comp.props} />;
          case "dashboard":
            return (
              <div key={comp.id} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {comp.title && <h3 className="col-span-full text-lg font-semibold">{comp.title}</h3>}
                {((comp.props.metrics || []) as AGUIMetricCardType[]).map((m, i) => (
                  <AgentMetricCard key={i} props={m as unknown as Record<string, unknown>} />
                ))}
              </div>
            );
          case "approval-card":
            return <AgentApprovalCard key={comp.id} props={comp.props} />;
          case "status-indicator":
            return (
              <div key={comp.id} className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                {(comp.props as { message?: string }).message || "Agent thinking..."}
              </div>
            );
          case "code-block":
            return (
              <Card key={comp.id}>
                {comp.title && <CardHeader><CardTitle>{comp.title}</CardTitle></CardHeader>}
                <CardContent>
                  <pre className="bg-muted p-4 rounded-md overflow-x-auto text-sm">
                    <code>{String((comp.props as { code?: string }).code || "")}</code>
                  </pre>
                </CardContent>
              </Card>
            );
          default:
            return (
              <Card key={comp.id}>
                <CardContent className="p-4 text-sm text-muted-foreground">
                  Unsupported component type: {comp.type}
                </CardContent>
              </Card>
            );
        }
      })}
    </div>
  );
}

export default AGUIRenderer;
