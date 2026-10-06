import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/chat";
import { MessageHeader } from "@/components/ResponseSection/MessageHeader";
import { MessageFooter } from "@/components/ResponseSection/MessageFooter";
import { CodeBlock } from "@/components/ResponseSection/CodeBlock";
import { AttachmentGallery } from "@/components/ResponseSection/AttachmentGallery";
import { EscalationApprovalCard } from "@/components/ResponseSection/EscalationApprovalCard";
import { PantrySourceChips } from "@/components/ResponseSection/PantrySourceChips";
import { WebSourceChips } from "@/components/ResponseSection/WebSourceChips";

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
      <div
        className="ml-auto max-w-[75%] break-words rounded-lg bg-latte px-4 py-2 text-espresso"
        data-testid="user-message"
      >
        <AttachmentGallery attachments={message.attachments} />
        {message.content}
      </div>
    );
  }

  return (
    <div
      className="w-full min-w-0 max-w-full break-words border-l-2 border-crema-amber py-3 pl-4"
      data-testid="assistant-message"
    >
      {message.pendingEscalationRecovered && (
        <p className="mb-1 text-xs italic text-medium-roast" data-testid="recovered-escalation-note">
          Recovered after a reload - the original message text isn&apos;t available.
        </p>
      )}
      <MessageHeader message={message} />
      <div className="mt-2 text-espresso">
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
            table({ children }) {
              return (
                <div className="my-2 overflow-x-auto">
                  <table className="w-full border-collapse border border-caramel text-sm">{children}</table>
                </div>
              );
            },
            th({ children }) {
              return <th className="border border-caramel bg-latte px-3 py-2 text-left font-semibold">{children}</th>;
            },
            td({ children }) {
              return <td className="border border-caramel px-3 py-2">{children}</td>;
            },
            ul({ children }) {
              return <ul className="my-2 list-disc space-y-1 pl-6">{children}</ul>;
            },
            ol({ children }) {
              return <ol className="my-2 list-decimal space-y-1 pl-6">{children}</ol>;
            },
            h1({ children }) {
              return <h1 className="mb-2 mt-4 text-xl font-bold">{children}</h1>;
            },
            h2({ children }) {
              return <h2 className="mb-2 mt-3 text-lg font-semibold">{children}</h2>;
            },
            h3({ children }) {
              return <h3 className="mb-1 mt-2 text-base font-semibold">{children}</h3>;
            },
            h4({ children }) {
              return <h4 className="mb-1 mt-2 text-sm font-semibold">{children}</h4>;
            },
            h5({ children }) {
              return <h5 className="mb-1 mt-2 text-sm font-semibold">{children}</h5>;
            },
            h6({ children }) {
              return <h6 className="mb-1 mt-2 text-sm font-semibold">{children}</h6>;
            },
            p({ children }) {
              return <p className="my-2 leading-[1.7]">{children}</p>;
            },
            blockquote({ children }) {
              return (
                <blockquote className="my-2 border-l-2 border-caramel pl-3 italic text-medium-roast">
                  {children}
                </blockquote>
              );
            },
            a({ children, href }) {
              return (
                <a href={href} className="text-crema-amber underline hover:opacity-80" target="_blank" rel="noreferrer">
                  {children}
                </a>
              );
            },
            strong({ children }) {
              return <strong className="font-semibold">{children}</strong>;
            },
            em({ children }) {
              return <em className="italic">{children}</em>;
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
      {!message.isStreaming && <WebSourceChips sources={message.webSources} />}
      {!message.isStreaming && <MessageFooter message={message} />}
    </div>
  );
}
