"use client";

import { useEffect, useState } from "react";

type Marketplace = { code: string; currency: string; frontend_domain: string; timezone: string };

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [marketplaces, setMarketplaces] = useState<Marketplace[]>([]);
  const [selected, setSelected] = useState("US");
  const [status, setStatus] = useState("正在读取站点配置…");

  useEffect(() => {
    fetch(`${API}/api/marketplaces`)
      .then((response) => response.json())
      .then((items: Marketplace[]) => {
        setMarketplaces(items);
        setStatus(items.length ? "站点配置已加载；等待数据源验证" : "暂无启用站点");
      })
      .catch(() => setStatus("API 暂不可用，请检查服务器状态"));
  }, []);

  const current = marketplaces.find((item) => item.code === selected);

  return (
    <main className="shell">
      <header className="header">
        <div><p className="eyebrow">AMAZONRELEASE MVP</p><h1>竞品选品工作台</h1><p className="muted">发现商品、核验数据、估算情景利润，再决定是否进入人工核验。</p></div>
        <label className="site-picker">站点<select value={selected} onChange={(event) => setSelected(event.target.value)}>{marketplaces.map((item) => <option key={item.code} value={item.code}>{item.code} · {item.currency}</option>)}</select></label>
      </header>
      <section className="notice"><strong>{status}</strong><span>销量字段会明确标注实际、估算、代理或不可用；当前不展示未经验证的生产数据。</span></section>
      <section className="grid">
        <article className="card"><span className="label">当前站点</span><strong>{current?.code ?? "—"}</strong><span>{current?.frontend_domain ?? "等待 API"}</span></article>
        <article className="card"><span className="label">货币 / 时区</span><strong>{current?.currency ?? "—"}</strong><span>{current?.timezone ?? "—"}</span></article>
        <article className="card"><span className="label">已验证商品</span><strong>0</strong><span>完成数据源验证后显示</span></article>
      </section>
      <section className="panel"><h2>下一步</h2><div className="steps"><div><b>01</b><span>确认目标类目、browse node 和关键词</span></div><div><b>02</b><span>导入 US/AU 各 50 个 ASIN 样本</span></div><div><b>03</b><span>完成 Keepa / SP-API 授权与字段验证</span></div></div></section>
    </main>
  );
}
