import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Check,
  Copy,
  MoreHorizontal,
  RotateCcw,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { ChatResponse } from "../types";

interface Props {
  onAsk: (question: string) => Promise<ChatResponse>;
}

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  question?: string;
  sources?: ChatResponse["sources"];
  isLoading?: boolean;
};

const SUGGESTED_PROMPTS = [
  "What does this repository do?",
  "How is this project structured?",
  "Which files should a new developer read first?",
  "Where is authentication implemented?",
  "What risks do you see in this codebase?",
  "How would I run this project locally?",
];

function buildId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function ChatPanel({ onAsk }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [likedMessageIds, setLikedMessageIds] = useState<Record<string, boolean>>(
    {}
  );
  const [dislikedMessageIds, setDislikedMessageIds] = useState<
    Record<string, boolean>
  >({});
  const [openMoreMenuId, setOpenMoreMenuId] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const emptyState = useMemo(() => messages.length === 0, [messages.length]);

  const autoResize = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
  };

  useEffect(() => {
    autoResize();
  }, [question]);

  useEffect(() => {
    const closeMenu = () => setOpenMoreMenuId(null);
    window.addEventListener("click", closeMenu);
    return () => window.removeEventListener("click", closeMenu);
  }, []);

  const submitQuestion = async (rawQuestion: string) => {
    const trimmed = rawQuestion.trim();
    if (!trimmed || loading) return;

    const userMessage: ChatMessage = {
      id: buildId(),
      role: "user",
      content: trimmed,
    };

    const loadingMessage: ChatMessage = {
      id: buildId(),
      role: "assistant",
      content: "Searching repository context and drafting a grounded answer…",
      isLoading: true,
      question: trimmed,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setQuestion("");
    setLoading(true);
    setError(null);
    setOpenMoreMenuId(null);

    try {
      const result = await onAsk(trimmed);

      setMessages((prev) =>
        prev.map((message) =>
          message.id === loadingMessage.id
            ? {
                id: buildId(),
                role: "assistant",
                content: result.answer,
                sources: result.sources,
                question: trimmed,
              }
            : message
        )
      );
    } catch {
      setMessages((prev) =>
        prev.filter((message) => message.id !== loadingMessage.id)
      );
      setError("Unable to get an answer right now.");
    } finally {
      setLoading(false);
    }
  };

  const regenerateAnswer = async (oldQuestion?: string) => {
    if (!oldQuestion) return;
    await submitQuestion(oldQuestion);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await submitQuestion(question);
  };

  const handlePromptClick = async (prompt: string) => {
    await submitQuestion(prompt);
  };

  const handleKeyDown = async (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await submitQuestion(question);
    }
  };

  const copyText = async (messageId: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);

      setTimeout(() => {
        setCopiedMessageId((current) => (current === messageId ? null : current));
      }, 1500);
    } catch {
      setError("Unable to copy text right now.");
    }
  };

  const handleLike = (messageId: string) => {
    setLikedMessageIds((prev) => {
      const nextValue = !prev[messageId];
      return { ...prev, [messageId]: nextValue };
    });

    setDislikedMessageIds((prev) => ({
      ...prev,
      [messageId]: false,
    }));
  };

  const handleDislike = (messageId: string) => {
    setDislikedMessageIds((prev) => {
      const nextValue = !prev[messageId];
      return { ...prev, [messageId]: nextValue };
    });

    setLikedMessageIds((prev) => ({
      ...prev,
      [messageId]: false,
    }));
  };

  const toggleMoreMenu = (
    event: React.MouseEvent<HTMLButtonElement>,
    messageId: string
  ) => {
    event.stopPropagation();
    setOpenMoreMenuId((current) => (current === messageId ? null : messageId));
  };

  return (
    <section className="card flex h-[760px] flex-col overflow-hidden p-0">
      <div className="border-b border-slate-800 px-6 py-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-white">
              Repository Copilot
            </h3>
            <p className="mt-1 text-sm text-slate-400">
              Ask grounded questions about architecture, setup, risks, files,
              and implementation details.
            </p>
          </div>

          <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs font-medium text-slate-300">
            Repo-aware chat
          </span>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto px-6 py-5 pb-20"
      >
        {emptyState ? (
          <div className="flex h-full flex-col justify-center">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5">
              <p className="text-base font-medium text-slate-100">
                Start a conversation about this repository
              </p>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Ask about the codebase purpose, architecture, key files, setup,
                risks, or implementation details.
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => void handlePromptClick(prompt)}
                    className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-600 hover:bg-slate-800"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => {
            const isUser = message.role === "user";
            const isLiked = !!likedMessageIds[message.id];
            const isDisliked = !!dislikedMessageIds[message.id];
            const isMenuOpen = openMoreMenuId === message.id;
            const isCopied = copiedMessageId === message.id;

            return (
              <div
                key={message.id}
                className={`flex ${isUser ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`relative max-w-[85%] rounded-2xl border px-4 py-3 shadow-sm overflow-visible ${
                    isUser
                      ? "border-violet-500/30 bg-violet-500/15 text-slate-100"
                      : "border-slate-800 bg-slate-950/70 text-slate-200"
                  }`}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className={`text-xs font-semibold uppercase tracking-wide ${
                        isUser ? "text-violet-200" : "text-slate-400"
                      }`}
                    >
                      {isUser ? "You" : "CodeLens AI"}
                    </span>
                  </div>

                  <div className="whitespace-pre-wrap break-words text-sm leading-7">
                    {message.isLoading ? (
                      <div className="flex items-center gap-3">
                        <span className="inline-flex h-2.5 w-2.5 animate-pulse rounded-full bg-cyan-400" />
                        <span>{message.content}</span>
                      </div>
                    ) : (
                      message.content
                    )}
                  </div>

                  {!isUser &&
                  !message.isLoading &&
                  message.sources &&
                  message.sources.length > 0 ? (
                    <div className="mt-4">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Sources
                      </p>

                      <div className="mt-2 flex flex-wrap gap-2">
                        {message.sources.map((source) => (
                          <details
                            key={`${source.file_path}-${source.snippet.slice(
                              0,
                              24
                            )}`}
                            className="group rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2"
                          >
                            <summary className="cursor-pointer list-none text-sm font-medium text-cyan-300">
                              {source.file_path}
                            </summary>

                            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
                              {source.snippet}
                            </p>
                          </details>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {!isUser && !message.isLoading ? (
                    <div className="mt-4 flex items-center gap-3 border-t border-slate-800 pt-3 text-slate-400">
                      <button
                        onClick={() => void copyText(message.id, message.content)}
                        className={`transition hover:text-white ${
                          isCopied ? "text-emerald-300" : ""
                        }`}
                        title="Copy"
                        type="button"
                      >
                        {isCopied ? <Check size={18} /> : <Copy size={18} />}
                      </button>

                      <button
                        onClick={() => handleLike(message.id)}
                        className={`transition hover:text-white ${
                          isLiked ? "text-emerald-300" : ""
                        }`}
                        title="Like"
                        type="button"
                      >
                        <ThumbsUp size={18} />
                      </button>

                      <button
                        onClick={() => handleDislike(message.id)}
                        className={`transition hover:text-white ${
                          isDisliked ? "text-rose-300" : ""
                        }`}
                        title="Dislike"
                        type="button"
                      >
                        <ThumbsDown size={18} />
                      </button>

                      <button
                        onClick={() => void regenerateAnswer(message.question)}
                        className="transition hover:text-white"
                        title="Regenerate"
                        type="button"
                      >
                        <RotateCcw size={18} />
                      </button>

                      <div className="relative">
                        <button
                          onClick={(event) => toggleMoreMenu(event, message.id)}
                          className="transition hover:text-white"
                          title="More"
                          type="button"
                        >
                          <MoreHorizontal size={18} />
                        </button>

                        {isMenuOpen ? (
                          <div
                            className="absolute right-0 top-8 z-20 min-w-[180px] rounded-xl border border-slate-800 bg-slate-950 p-2 shadow-2xl"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <button
                              type="button"
                              onClick={() => {
                                void copyText(message.id, message.content);
                                setOpenMoreMenuId(null);
                              }}
                              className="flex w-full items-center rounded-lg px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-slate-900"
                            >
                              Copy answer
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                void regenerateAnswer(message.question);
                                setOpenMoreMenuId(null);
                              }}
                              className="flex w-full items-center rounded-lg px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-slate-900"
                            >
                              Regenerate answer
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="border-t border-slate-800 bg-slate-950/70 px-6 py-5">
        {!emptyState ? (
          <div className="mb-3 flex flex-wrap gap-2">
            {SUGGESTED_PROMPTS.slice(0, 4).map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => void handlePromptClick(prompt)}
                className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-600 hover:bg-slate-800"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 shadow-inner">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about architecture, setup, authentication, risks, or specific files..."
              className="max-h-[220px] min-h-[56px] w-full resize-none bg-transparent text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-500"
              disabled={loading}
            />
          </div>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Press Enter to send • Shift + Enter for a new line
            </p>

            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="rounded-xl bg-violet-500 px-4 py-2 font-semibold text-white transition hover:bg-violet-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Thinking..." : "Send"}
            </button>
          </div>
        </form>

        {error ? (
          <p className="mt-3 text-sm text-rose-300">{error}</p>
        ) : null}
      </div>
    </section>
  );
}