import Link from "next/link";

export function StoreHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link href="/" className="block">
          <p className="text-2xl font-bold tracking-tight text-slate-950">
            Kairo
          </p>

          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
            Marketplace
          </p>
        </Link>

        <nav className="flex items-center gap-6 text-sm font-medium text-slate-600">
          <Link href="/" className="transition hover:text-slate-950">
            Shop
          </Link>

          <a href="#catalogue" className="transition hover:text-slate-950">
            Categories
          </a>

          <span className="cursor-not-allowed text-slate-400">
            Orders
          </span>

          <span className="cursor-not-allowed text-slate-400">
            Cart
          </span>
        </nav>
      </div>
    </header>
  );
}
