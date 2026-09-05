import io
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.extensions import db
from app.models import Projeto, Alocacao, Despesa
from app.projetos.routes import _pode_ver_projeto

relatorios_bp = Blueprint("relatorios", __name__)

ROTULOS = {
    "ativo": "Ativo", "inativo": "Inativo", "encerrado": "Encerrado",
    "pendente_aprovacao": "Pendente de aprovação", "reprovado": "Reprovado",
    "custeio": "Custeio", "capital": "Capital", "devolucao": "Devolução",
    "lancada": "Lançada", "estornada": "Estornada", "reprovada": "Reprovada",
    "em_analise": "Em análise", "aceita": "Aceita",
}


def _moeda(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _responsavel_do_projeto(projeto, alocacoes):
    if projeto.criado_por:
        return projeto.criado_por
    coordenador = next((a for a in alocacoes if a.papel_projeto == "coordenador"), None)
    return coordenador.usuario if coordenador else None


@relatorios_bp.route("/projetos/<int:projeto_id>/relatorio")
@login_required
def relatorio_projeto(projeto_id):
    projeto = db.session.get(Projeto, projeto_id)
    if projeto is None:
        flash("Projeto não encontrado.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if not _pode_ver_projeto(projeto_id):
        flash("Você não tem acesso a este projeto.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    alocacoes = Alocacao.query.filter_by(projeto_id=projeto.id).all()
    total_alocado = sum((a.valor_alocado for a in alocacoes), 0)
    saldo_nao_alocado = projeto.valor_total - total_alocado

    despesas = (
        Despesa.query.join(Alocacao)
        .filter(Alocacao.projeto_id == projeto.id)
        .order_by(Despesa.data)
        .all()
    )

    total_despesas = sum((d.valor for d in despesas if d.status == "lancada"), 0)
    saldo_disponivel = projeto.valor_total - total_despesas

    responsavel = _responsavel_do_projeto(projeto, alocacoes)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=16, spaceAfter=4)
    subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16)
    secao = ParagraphStyle("secao", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=8)

    elementos = []
    elementos.append(Paragraph("Prestação de Contas", titulo))
    elementos.append(Paragraph("Sistema de Controle Financeiro — PROPI/UFAC", subtitulo))

    elementos.append(Paragraph("Dados do projeto", secao))
    dados_projeto = [
        ["Nome", projeto.nome],
        ["Vigência", f"{projeto.vigencia_inicio.strftime('%d/%m/%Y')} a {projeto.vigencia_fim.strftime('%d/%m/%Y')}"],
        ["Status", ROTULOS.get(projeto.status, projeto.status)],
        ["Responsável", responsavel.nome if responsavel else "—"],
        ["CPF do responsável", (responsavel.cpf or "—") if responsavel else "—"],
    ]
    t = Table(dados_projeto, colWidths=[4 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    elementos.append(t)

    elementos.append(Paragraph("Resumo financeiro", secao))
    resumo = [
        ["Valor total do projeto", _moeda(projeto.valor_total)],
        ["Total alocado (planejado)", _moeda(total_alocado)],
        ["Saldo não alocado", _moeda(saldo_nao_alocado)],
        ["Total gasto (despesas lançadas)", _moeda(total_despesas)],
        ["Saldo do projeto", _moeda(saldo_disponivel)],
    ]
    t = Table(resumo, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elementos.append(t)

    elementos.append(Paragraph("Alocações", secao))
    if alocacoes:
        linhas = [["Responsável", "Tipo de alocação", "Categoria", "Valor alocado"]]
        for a in alocacoes:
            linhas.append([
                a.usuario.nome,
                a.tipo_alocacao.nome if a.tipo_alocacao else "—",
                ROTULOS.get(a.categoria, a.categoria),
                _moeda(a.valor_alocado),
            ])
        t = Table(linhas, colWidths=[5 * cm, 5 * cm, 3 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhuma alocação cadastrada.", styles["Normal"]))

    elementos.append(Paragraph("Despesas lançadas", secao))
    if despesas:
        linhas = [["Data", "Natureza", "Favorecido", "Nº comprovante fiscal", "Valor", "Status"]]
        for d in despesas:
            favorecido = d.fornecedor
            if d.cnpj_favorecido:
                favorecido += f" ({d.cnpj_favorecido})"
            linhas.append([
                d.data.strftime("%d/%m/%Y"),
                ROTULOS.get(d.natureza, d.natureza),
                favorecido,
                d.numero_comprovante_fiscal or "—",
                _moeda(d.valor),
                ROTULOS.get(d.status, d.status),
            ])
        t = Table(linhas, colWidths=[2 * cm, 2.3 * cm, 5 * cm, 2.7 * cm, 2.5 * cm, 2.5 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhuma despesa lançada.", styles["Normal"]))

    elementos.append(Spacer(1, 24))
    rodape = ParagraphStyle("rodape", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    elementos.append(Paragraph(f"Relatório gerado em {agora} por {current_user.nome}.", rodape))

    doc.build(elementos)
    buffer.seek(0)

    nome_arquivo = f"prestacao_contas_{projeto.nome.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


@relatorios_bp.route("/alocacoes/<int:alocacao_id>/relatorio")
@login_required
def relatorio_alocacao(alocacao_id):
    """Prestação de contas da verba de UMA pessoa dentro do projeto — só
    a alocação principal dela, as sub-alocações e despesas relacionadas
    (decisão de 19/09/2026: prestação passou a ser por pessoa)."""
    alocacao = db.session.get(Alocacao, alocacao_id)
    if alocacao is None:
        flash("Alocação não encontrada.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if alocacao.alocacao_pai_id is not None:
        flash("Relatório disponível apenas para a alocação principal.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    if current_user.papel != "administrador" and current_user.id != alocacao.usuario_id:
        flash("Você não tem permissão para ver este relatório.", "erro")
        return redirect(url_for("projetos.listar_projetos"))

    projeto = alocacao.projeto
    sub_alocacoes = alocacao.sub_alocacoes
    ids_alocacoes = [alocacao.id] + [s.id for s in sub_alocacoes]

    despesas = (
        Despesa.query.filter(Despesa.alocacao_id.in_(ids_alocacoes))
        .order_by(Despesa.data)
        .all()
    )

    total_despesas = sum((d.valor for d in despesas if d.status == "lancada"), 0)
    saldo = alocacao.valor_alocado - total_despesas

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=16, spaceAfter=4)
    subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16)
    secao = ParagraphStyle("secao", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=8)

    elementos = []
    elementos.append(Paragraph("Prestação de Contas — Responsável", titulo))
    elementos.append(Paragraph("Sistema de Controle Financeiro — PROPI/UFAC", subtitulo))

    elementos.append(Paragraph("Dados", secao))
    dados = [
        ["Projeto", projeto.nome],
        ["Vigência", f"{projeto.vigencia_inicio.strftime('%d/%m/%Y')} a {projeto.vigencia_fim.strftime('%d/%m/%Y')}"],
        ["Responsável", alocacao.usuario.nome],
        ["CPF do responsável", alocacao.usuario.cpf or "—"],
        ["Status da prestação", ROTULOS.get(alocacao.status_prestacao_contas, "Não enviada") if alocacao.status_prestacao_contas else "Não enviada"],
    ]
    t = Table(dados, colWidths=[4 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    elementos.append(t)

    elementos.append(Paragraph("Resumo financeiro desta verba", secao))
    resumo = [
        ["Valor alocado", _moeda(alocacao.valor_alocado)],
        ["Total gasto (despesas lançadas)", _moeda(total_despesas)],
        ["Saldo", _moeda(saldo)],
    ]
    t = Table(resumo, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elementos.append(t)

    elementos.append(Paragraph("Alocações por tipo de despesa", secao))
    if sub_alocacoes:
        linhas = [["Tipo", "Categoria", "Status", "Valor"]]
        for s in sub_alocacoes:
            linhas.append([
                s.tipo_alocacao.nome if s.tipo_alocacao else "—",
                ROTULOS.get(s.categoria, s.categoria),
                ROTULOS.get(s.status, s.status),
                _moeda(s.valor_alocado),
            ])
        t = Table(linhas, colWidths=[5 * cm, 4 * cm, 3 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhuma alocação por tipo cadastrada.", styles["Normal"]))

    elementos.append(Paragraph("Despesas lançadas", secao))
    if despesas:
        linhas = [["Data", "Natureza", "Favorecido", "Nº comprovante fiscal", "Valor", "Status"]]
        for d in despesas:
            favorecido = d.fornecedor
            if d.cnpj_favorecido:
                favorecido += f" ({d.cnpj_favorecido})"
            linhas.append([
                d.data.strftime("%d/%m/%Y"),
                ROTULOS.get(d.natureza, d.natureza),
                favorecido,
                d.numero_comprovante_fiscal or "—",
                _moeda(d.valor),
                ROTULOS.get(d.status, d.status),
            ])
        t = Table(linhas, colWidths=[2 * cm, 2.3 * cm, 5 * cm, 2.7 * cm, 2.5 * cm, 2.5 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhuma despesa lançada.", styles["Normal"]))

    elementos.append(Spacer(1, 24))
    rodape = ParagraphStyle("rodape", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    elementos.append(Paragraph(f"Relatório gerado em {agora} por {current_user.nome}.", rodape))

    doc.build(elementos)
    buffer.seek(0)

    nome_arquivo = f"prestacao_contas_{alocacao.usuario.nome.replace(' ', '_')}_{projeto.nome.replace(' ', '_')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


@relatorios_bp.route("/relatorios/consolidado")
@login_required
def relatorio_consolidado():
    if current_user.papel != "administrador":
        flash("Você não tem permissão para acessar esta página.", "erro")
        return redirect(url_for("auth.painel"))

    projetos = Projeto.query.order_by(Projeto.nome).all()

    linhas_projetos = []
    total_administrado = Decimal("0")
    total_gasto_geral = Decimal("0")

    for projeto in projetos:
        total_gasto = (
            db.session.query(db.func.coalesce(db.func.sum(Despesa.valor), 0))
            .join(Alocacao)
            .filter(Alocacao.projeto_id == projeto.id, Despesa.status == "lancada")
            .scalar()
        )
        total_gasto = Decimal(total_gasto)
        saldo = projeto.valor_total - total_gasto

        total_administrado += projeto.valor_total
        total_gasto_geral += total_gasto

        alocacoes = Alocacao.query.filter_by(projeto_id=projeto.id).all()
        responsavel = _responsavel_do_projeto(projeto, alocacoes)

        linhas_projetos.append({
            "projeto": projeto,
            "responsavel": responsavel.nome if responsavel else "—",
            "total_gasto": total_gasto,
            "saldo": saldo,
        })

    saldo_geral = total_administrado - total_gasto_geral

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=16, spaceAfter=4)
    subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=16)
    secao = ParagraphStyle("secao", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=8)

    elementos = []
    elementos.append(Paragraph("Relatório Consolidado de Projetos", titulo))
    elementos.append(Paragraph("Sistema de Controle Financeiro — PROPI/UFAC", subtitulo))

    elementos.append(Paragraph("Resumo geral", secao))
    resumo = [
        ["Total de projetos", str(len(projetos))],
        ["Total administrado", _moeda(total_administrado)],
        ["Total gasto (despesas lançadas)", _moeda(total_gasto_geral)],
        ["Saldo geral", _moeda(saldo_geral)],
    ]
    t = Table(resumo, colWidths=[8 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elementos.append(t)

    elementos.append(Paragraph("Projetos", secao))
    if linhas_projetos:
        linhas = [["Projeto", "Responsável", "Status", "Valor total", "Total gasto", "Saldo"]]
        for item in linhas_projetos:
            linhas.append([
                item["projeto"].nome,
                item["responsavel"],
                ROTULOS.get(item["projeto"].status, item["projeto"].status),
                _moeda(item["projeto"].valor_total),
                _moeda(item["total_gasto"]),
                _moeda(item["saldo"]),
            ])
        t = Table(linhas, colWidths=[4.5 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B3A55")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        elementos.append(t)
    else:
        elementos.append(Paragraph("Nenhum projeto cadastrado.", styles["Normal"]))

    elementos.append(Spacer(1, 24))
    rodape = ParagraphStyle("rodape", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    elementos.append(Paragraph(f"Relatório gerado em {agora} por {current_user.nome}.", rodape))

    doc.build(elementos)
    buffer.seek(0)

    nome_arquivo = f"relatorio_consolidado_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")