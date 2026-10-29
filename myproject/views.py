
import base64
import io
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import yfinance as yf

from django.shortcuts import render


TICKER = "^NSEI"
START = "2007-08-01"
END = "2009-07-01"  # Exclusive; includes June 30, 2009


def load_returns():
    """Download Nifty 50 historical prices and calculate daily returns."""
    prices = yf.Ticker(TICKER).history(
        start=START,
        end=END,
        auto_adjust=True
    )["Close"].dropna()

    if len(prices) < 100:
        raise ValueError(
            "Not enough historical data downloaded. Please try again later."
        )

    returns = prices.pct_change().dropna()
    period = (
        f"{prices.index[0]:%d %b %Y} - "
        f"{prices.index[-1]:%d %b %Y}"
    )

    return list(returns), period


def calc_svar(returns, portfolio, confidence):
    """Calculate historical one-day SVaR as a positive loss."""
    worst_first = sorted(returns)
    index = min(
        int((1 - confidence) * len(worst_first)),
        len(worst_first) - 1
    )
    return max(0, portfolio * -worst_first[index])


def rupees(number):
    """Format a number using Indian-style commas."""
    amount = f"{round(number):,}"
    last_three = amount.replace(",", "")[-3:]
    remaining = amount.replace(",", "")[:-3]

    if remaining:
        remaining = re.sub(r"\B(?=(\d{2})+(?!\d))", ",", remaining)
        amount = remaining + "," + last_three
    else:
        amount = last_three

    return "₹" + amount


def make_graphs(returns, period, portfolio, confidence):
    """Generate the three SVaR charts as a Base64 PNG image."""
    svar = calc_svar(returns, portfolio, confidence)
    svar95 = calc_svar(returns, portfolio, 0.95)
    svar99 = calc_svar(returns, portfolio, 0.99)

    graphs = [
        (
            "Portfolio Value vs. SVaR",
            ["Portfolio Value", "SVaR (loss)"],
            [portfolio, svar],
            ["#1b3d2f", "#b91c1c"]
        ),
        (
            "Portfolio Value After Stress",
            ["Before stress", "After stress"],
            [portfolio, portfolio - svar],
            ["#1b3d2f", "#d97706"]
        ),
        (
            "SVaR by Confidence Level",
            ["95% confidence", "99% confidence"],
            [svar95, svar99],
            ["#2563eb", "#b91c1c"]
        ),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, (title, labels, values, colors) in zip(axes, graphs):
        bars = ax.bar(labels, values, color=colors)
        ax.bar_label(
            bars,
            labels=[rupees(value) for value in values]
        )
        ax.set_title(title)
        ax.set_ylabel("Amount (₹)")
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda value, _: rupees(value))
        )
        ax.tick_params(axis="x", labelrotation=10)

    fig.suptitle(f"SVaR (1-day) - Nifty 50 stress period {period}")
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def home(request):
    return render(request, "index.html")


def calculator(request):
    context = {}

    if request.method == "POST":
        try:
            portfolio = float(request.POST.get("portfolio", ""))
            confidence_input = request.POST.get("confidence", "95")

            if portfolio <= 0:
                raise ValueError("Portfolio value must be greater than zero.")

            if not portfolio < float("inf"):
                raise ValueError("Enter a valid portfolio value.")

            if confidence_input not in ("95", "99"):
                raise ValueError("Choose either 95% or 99% confidence.")

            confidence = int(confidence_input) / 100

            returns, period = load_returns()
            svar = calc_svar(returns, portfolio, confidence)
            graph = make_graphs(returns, period, portfolio, confidence)

            context.update({
                "portfolio": portfolio,
                "portfolio_display": rupees(portfolio),
                "confidence": confidence_input,
                "stress_period": period,
                "daily_returns": len(returns),
                "svar": svar,
                "svar_display": rupees(svar),
                "svar_percent": f"{svar / portfolio * 100:.2f}",
                "after_stress": rupees(portfolio - svar),
                "graph": graph,
            })

        except (ValueError, TypeError, OverflowError) as error:
            context["error"] = str(error)

        except Exception:
            context["error"] = (
                "Unable to calculate SVaR right now. "
                "Check your internet connection and try again."
            )

    return render(request, "calculator.html", context)