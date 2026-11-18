export default function Estado({ data, error }: { data: unknown; error: string | null }) {
  if (error) return <p className="rounded bg-red-50 p-3 text-red-700">No se pudo cargar: {error}</p>
  if (!data) return <p className="text-gray-500">Cargando…</p>
  return null
}
