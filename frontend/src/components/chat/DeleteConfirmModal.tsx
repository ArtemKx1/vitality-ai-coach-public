import { Button } from "@/components/ui/button"

interface DeleteConfirmModalProps {
  onConfirm: () => void
  onCancel: () => void
}

export function DeleteConfirmModal({ onConfirm, onCancel }: DeleteConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-obsidian/30 backdrop-blur-sm">
      <div className="bg-paper-white rounded-[20px] shadow-xl p-6 w-80 max-w-[90vw] space-y-4">
        <p className="text-sm font-inter text-obsidian font-medium">Delete conversation?</p>
        <p className="text-xs font-inter text-charcoal">This action cannot be undone.</p>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="default" size="sm" className="bg-red-500 hover:bg-red-600 text-white" onClick={onConfirm}>
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}
