import { onBeforeUnmount, ref } from 'vue'
import { fetchJob } from '../api/ingest'
import type { IngestJob } from '../types/models'

export function useJobPolling(onUpdate: (job: IngestJob) => void) {
  const polling = ref(false)
  let timer: number | null = null

  function stop() {
    polling.value = false
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  async function poll(jobId: string, attempts = 40) {
    stop()
    polling.value = true
    let remaining = attempts
    const tick = async () => {
      if (!polling.value || remaining <= 0) {
        stop()
        return
      }
      remaining -= 1
      try {
        const job = await fetchJob(jobId)
        onUpdate(job)
        if (job.status === 'completed' || job.status === 'failed') {
          stop()
          return
        }
      } catch {
        stop()
        return
      }
      timer = window.setTimeout(tick, 1200)
    }
    await tick()
  }

  onBeforeUnmount(stop)
  return { polling, poll, stop }
}
