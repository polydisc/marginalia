import { ApiError } from './api'

/** The outcome of an API call, ready to surface in the UI. */
export type Result = { ok: boolean; text: string }

/** notify() runs an API call, records the outcome, and returns it for inline use. */
export type Notify = (run: () => Promise<string>) => Promise<Result>

/**
 * Run an API call and map a failure to a patron-friendly {ok,text}. Unlike the
 * staff console's `notify` (which prefixes the status + domain code for an
 * operator), this surfaces the human `detail` message alone.
 */
export async function runApi(run: () => Promise<string>): Promise<Result> {
  try {
    return { ok: true, text: await run() }
  } catch (err) {
    if (err instanceof ApiError) return { ok: false, text: err.message }
    // Network / unexpected: keep it calm for a patron, detail to the console.
    console.error(err)
    return { ok: false, text: 'Something went wrong — please try again.' }
  }
}
