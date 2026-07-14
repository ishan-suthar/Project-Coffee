import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/chat";
import { MessageHeader } from "@/components/ResponseSection/MessageHeader";
import { MessageFooter } from "@/components/ResponseSection/MessageFooter";
import { CodeBlock } from "@/components/ResponseSection/CodeBlock";
import { AttachmentGallery } from "@/components/ResponseSection/AttachmentGallery";
import { EscalationApprovalCard } from "@/components/ResponseSection/EscalationApprovalCard";
import { PantrySourceChips } from "@/components/ResponseSection/PantrySourceChips";

/** True while a message's escalation is genuinely awaiting a decision -
 * live pause or a reload-recovered card (Brew 40). Once the next real
 * event arrives (live) or polling resolves it (recovered), isStreaming
 * flips false and the card disappears on its own. */
function hasOpenEscalationApproval(message: ChatMessage): boolean {
  return (
    message.escalation !== null &&
    message.isStreaming &&
    message.latestEvent?.event === "escalation_pending"
  );
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="ml-auto max-w-2xl rounded-lg bg-latte px-4 py-2 text-espresso" data-testid="user-message">
        <AttachmentGallery attachments={message.attachments} />
        {message.content}
      </div>
    );
  }

  return (
    <div className="mr-auto max-w-2xl rounded-lg border border-caramel bg-cream px-4 py-3" data-testid="assistant-message">
      {message.pendingEscalationRecovered && (
        <p className="mb-1 text-xs italic text-medium-roast" data-testid="recovered-escalation-note">
          Recovered after a reload - the original message text isn&apos;t available.
        </p>
      )}
      <MessageHeader message={message} />
      <div className="prose prose-sm mt-2 max-w-none text-espresso">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children }) {
              const isBlock = /language-/.test(className ?? "");
              if (!isBlock) {
                return <code className="rounded bg-latte px-1 font-mono">{children}</code>;
              }
              return <CodeBlock className={className}>{children}</CodeBlock>;
            },
          }}
        >
          {message.content}
        </ReactMarkdown>
        {message.isStreaming && <span className="animate-pulse text-medium-roast">▌</span>}
      </div>
      {message.errorMessage && (
        <p className="mt-2 text-sm text-crema-amber" data-testid="message-error">
          {message.errorMessage}
        </p>
      )}
      {hasOpenEscalationApproval(message) && <EscalationApprovalCard message={message} />}
      {!message.isStreaming && <PantrySourceChips sources={message.pantrySources} />}
      {!message.isStreaming && <MessageFooter message={message} />}
    </div>
  );
}
