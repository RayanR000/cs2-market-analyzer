const COOLDOWN_MS = 300000
let lastChainAt = 0
let changesMade = false

export const ChainPlugin = async ({ client }) => {
  return {
    "tool.execute.after": async (input) => {
      if (["write", "edit", "apply_patch"].includes(input.tool)) {
        changesMade = true
      }
    },
    event: async ({ event }) => {
      if (event.type !== "session.idle" || !changesMade) return

      const now = Date.now()
      if (now - lastChainAt < COOLDOWN_MS) return

      changesMade = false
      lastChainAt = now

      try {
        const sessionId = event.properties?.sessionId

        let id = sessionId
        if (!id) {
          const sessions = await client.session.list()
          const last = sessions?.data?.at?.(-1)
          if (last) id = last.id
        }
        if (!id) return

        await client.session.prompt({
          path: { id },
          body: {
            parts: [{
              type: "text",
              text: "Run @review, then @test, then @security on the recent changes.",
            }],
          },
        })
      } catch (err) {
        console.error("[chain-plugin] Failed:", err)
      }
    },
  }
}
