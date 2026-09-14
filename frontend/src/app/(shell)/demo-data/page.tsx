"use client";

import { motion } from "framer-motion";
import { Cpu, CreditCard, Database, Package, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSimCatalog } from "@/hooks/use-sim";
import { buttonMotion } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { SimCustomerCatalog, SimDevice, SimOrder, SimSubscription } from "@/types/sim";

type TableKey = "customers" | "subscriptions" | "devices" | "orders" | "profiles" | "outbox";

function flattenSubscriptions(customers: SimCustomerCatalog[]): SimSubscription[] {
  return customers.flatMap((customer) => customer.subscriptions);
}

function flattenDevices(customers: SimCustomerCatalog[]): SimDevice[] {
  return customers.flatMap((customer) => customer.devices);
}

export default function DemoDataPage() {
  const { data, isLoading, isFetching, refetch } = useSimCatalog();
  const customers = data?.customers ?? [];
  const orders = data?.orders ?? [];
  const profiles = data?.device_profiles ?? [];
  const outbox = data?.outbound_messages ?? [];
  const subscriptions = useMemo(() => flattenSubscriptions(customers), [customers]);
  const devices = useMemo(() => flattenDevices(customers), [customers]);
  const [activeTable, setActiveTable] = useState<TableKey>("customers");

  const totals = {
    customers: customers.length,
    subscriptions: subscriptions.length,
    devices: devices.length,
    orders: orders.length,
    profiles: profiles.length,
  };

  const tableOptions: Array<{
    key: TableKey;
    label: string;
    count: number;
  }> = [
    { key: "customers", label: "Customers", count: totals.customers },
    { key: "subscriptions", label: "Subscriptions", count: totals.subscriptions },
    { key: "devices", label: "Devices", count: totals.devices },
    { key: "orders", label: "Orders", count: totals.orders },
    { key: "profiles", label: "Device Profiles", count: totals.profiles },
    { key: "outbox", label: "Outbox", count: outbox.length },
  ];

  const customersById = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer])),
    [customers],
  );

  const renderActiveTable = () => {
    if (activeTable === "customers") {
      return (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">ID</TableHead>
              <TableHead>Full Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Phone</TableHead>
              <TableHead>Subscriptions</TableHead>
              <TableHead>Devices</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((customer) => (
              <TableRow key={customer.id}>
                <TableCell className="pl-4 font-mono text-xs">{customer.id}</TableCell>
                <TableCell>{customer.full_name}</TableCell>
                <TableCell>{customer.email}</TableCell>
                <TableCell>{customer.phone || "—"}</TableCell>
                <TableCell>{customer.subscriptions.length}</TableCell>
                <TableCell>{customer.devices.length}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    if (activeTable === "subscriptions") {
      return (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">ID</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Customer ID</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Monthly Price</TableHead>
              <TableHead>Cancelled At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {subscriptions.map((subscription) => (
              <TableRow key={subscription.id}>
                <TableCell className="pl-4 font-mono text-xs">{subscription.id}</TableCell>
                <TableCell>{customersById.get(subscription.customer_id)?.full_name ?? "Unknown"}</TableCell>
                <TableCell className="font-mono text-xs">{subscription.customer_id}</TableCell>
                <TableCell>{subscription.plan_name}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{subscription.status}</Badge>
                </TableCell>
                <TableCell>${subscription.monthly_price_usd}</TableCell>
                <TableCell>{subscription.cancelled_at || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    if (activeTable === "orders") {
      return (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">Order #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Delivery</TableHead>
              <TableHead>Fulfillment</TableHead>
              <TableHead>Delivery Status</TableHead>
              <TableHead>Return Status</TableHead>
              <TableHead>Refund Status</TableHead>
              <TableHead>Tracking</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {orders.map((order: SimOrder) => (
              <TableRow key={order.id}>
                <TableCell className="pl-4 font-mono text-xs">#{order.order_number}</TableCell>
                <TableCell>{customersById.get(order.customer_id)?.full_name ?? "Unknown"}</TableCell>
                <TableCell>
                  <Badge variant="outline">{order.channel}</Badge>
                </TableCell>
                <TableCell>{order.customer_email}</TableCell>
                <TableCell>{order.delivery_date}</TableCell>
                <TableCell>
                  <Badge variant="outline">{order.fulfillment_status}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{order.delivery_status || "—"}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{order.return_status || "none"}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{order.refund_status || "none"}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{order.tracking_number || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    if (activeTable === "profiles") {
      return (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">Serial</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Family</TableHead>
              <TableHead>Segment</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Health</TableHead>
              <TableHead>SIM Triage</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {profiles.map((profile) => (
              <TableRow key={profile.serial_number}>
                <TableCell className="pl-4 font-mono text-xs">{profile.serial_number}</TableCell>
                <TableCell>{profile.model}</TableCell>
                <TableCell>
                  <Badge variant="outline">{profile.camera_family}</Badge>
                </TableCell>
                <TableCell>{profile.segment}</TableCell>
                <TableCell>{profile.customer_email}</TableCell>
                <TableCell>{profile.health_score || "—"}</TableCell>
                <TableCell>{profile.sim_triage_conclusion || "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    if (activeTable === "outbox") {
      return (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>To</TableHead>
              <TableHead>Created At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {outbox.map((message) => (
              <TableRow key={message.id}>
                <TableCell className="pl-4 font-mono text-xs">{message.id}</TableCell>
                <TableCell>
                  <Badge variant="outline">
                    {message.message_kind || message.related_entity_type || "message"}
                  </Badge>
                </TableCell>
                <TableCell>{message.subject}</TableCell>
                <TableCell>{message.to_address}</TableCell>
                <TableCell>{message.created_at ? new Date(message.created_at).toLocaleString() : "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }

    return (
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">ID</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Customer ID</TableHead>
            <TableHead>Serial Number</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Purchase Date</TableHead>
            <TableHead>Return Reason</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {devices.map((device) => (
            <TableRow key={device.id}>
              <TableCell className="pl-4 font-mono text-xs">{device.id}</TableCell>
              <TableCell>{customersById.get(device.customer_id)?.full_name ?? "Unknown"}</TableCell>
              <TableCell className="font-mono text-xs">{device.customer_id}</TableCell>
              <TableCell className="font-mono text-xs">{device.serial_number}</TableCell>
              <TableCell>{device.model}</TableCell>
              <TableCell>
                <Badge variant="secondary">{device.status}</Badge>
              </TableCell>
              <TableCell>{device.purchase_date || "—"}</TableCell>
              <TableCell>{device.return_reason || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  };

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="page-header">Demo Data</h2>
          <p className="page-description">
            Browse seeded simulation tables. Select a table to view all rows and columns.
          </p>
        </div>
        <motion.div {...buttonMotion}>
          <Button variant="outline" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={cn("mr-2 h-4 w-4", isFetching && "animate-spin")} />
            Refresh
          </Button>
        </motion.div>
      </div>

      <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Customers", value: totals.customers, icon: Database },
          { label: "Subscriptions", value: totals.subscriptions, icon: CreditCard },
          { label: "Devices", value: totals.devices, icon: Cpu },
          { label: "Orders", value: totals.orders, icon: Package },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="surface-card flex items-center gap-3 px-5 py-4">
              <div className="rounded-xl bg-primary/10 p-2.5 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                <p className="text-xl font-semibold tabular-nums text-foreground">{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="surface-card h-48 animate-pulse bg-muted/40" />
          ))}
        </div>
      ) : customers.length === 0 ? (
        <div className="surface-card flex flex-col items-center justify-center border-dashed px-8 py-20 text-center">
          <div className="mb-4 rounded-2xl bg-primary/10 p-4 text-primary">
            <Database className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-semibold">No simulation data</h3>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            Run migrations so the seeded demo tables are loaded.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="surface-card p-4">
            <div className="flex flex-wrap gap-2">
              {tableOptions.map((table) => (
                <Button
                  key={table.key}
                  variant={activeTable === table.key ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveTable(table.key)}
                >
                  {table.label}
                  <Badge
                    variant={activeTable === table.key ? "secondary" : "outline"}
                    className="ml-2"
                  >
                    {table.count}
                  </Badge>
                </Button>
              ))}
            </div>
          </div>

          <motion.div
            key={activeTable}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="surface-card overflow-hidden"
          >
            {renderActiveTable()}
          </motion.div>
        </div>
      )}

      <p className="mt-8 text-xs leading-relaxed text-muted-foreground">
        Tip: try Classic pairing with alex.rivera@example.com (NX-PRO-30001), Connect SIM issues with
        B2-MINI-50001, or hardware lookup with NX-ONE-20022.
      </p>
    </div>
  );
}
