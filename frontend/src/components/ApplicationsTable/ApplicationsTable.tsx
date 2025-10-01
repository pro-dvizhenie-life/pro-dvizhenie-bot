import { Group, Pagination, Table, TextInput } from "@mantine/core";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState
} from "@tanstack/react-table";
import React, { useState } from "react";
import type { IApplication } from "src/shared/const/testApplicationsData";

const columns = [
  {
    accessorKey: "applicationNumber",
    header: () => <span>Номер заявки</span>,
  },
  {
    accessorKey: "applicationDate",
    header: () => <span>Дата заявки</span>,
  },
  {
    accessorKey: "contactPerson",
    header: () => <span>Контактное лицо</span>,
  },
  {
    accessorKey: "city",
    header: () => <span>Город</span>,
  },
  {
    accessorKey: "applicationStatus",
    header: () => <span>Статус заявки</span>,
  },
];

interface Props {
  className?: string;
  applications: IApplication[];
}
export const ApplicationsTable: React.FC<Props> = ({
  className,
  applications,
}) => {
  const [data] = useState<IApplication[]>(() => [...applications]);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
      pagination: {
        pageSize: 4,
        pageIndex: 0,
      },
    },
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    onGlobalFilterChange: setGlobalFilter,
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className={className}>
      <TextInput
        placeholder="Поиск"
        value={globalFilter ?? ""}
        onChange={(event) => setGlobalFilter(event.target.value)}
      />
      <Table withColumnBorders>
        <Table.Thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <Table.Tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <Table.Th key={header.id}>
                  <div onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </div>
                </Table.Th>
              ))}
            </Table.Tr>
          ))}
        </Table.Thead>
        <Table.Tbody>
          {table.getRowModel().rows.map((row) => (
            <Table.Tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <Table.Td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Pagination.Root total={table.getPageCount()}>
        <Group gap={5} justify="flex-end" >
          <Pagination.First
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          />
          <Pagination.Previous
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          />
          <Pagination.Items />
          <Pagination.Next
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          />
          <Pagination.Last
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          />
        </Group>
      </Pagination.Root>
    </div>
  );
};
