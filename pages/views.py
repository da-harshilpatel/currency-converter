from django.shortcuts import render
from .data_processing import convert, etl_process, change_rate, show_chart, forecast

def currency_converter_view(request):
    # Initialize variables
    source_amount = None
    source_currency = None
    dest_currency = None
    converted_amount = None
    error = None
    chart_html = None
    forecast_html = None

    # Process the form submission
    if request.method == "POST":
        try:
            # Get form data
            source_amount = float(request.POST.get("source_amount", 0))
            source_currency = request.POST.get("source_currency")
            dest_currency = request.POST.get("dest_currency")

            # Perform conversion
            converted_amount = convert(source_amount, source_currency, dest_currency)

        except Exception as e:
            error = str(e)

    # Generate charts (move outside the try block)
    if source_currency and dest_currency:
        try:
            # Generate historical trends chart
            df, chart_fig = show_chart(source_currency, dest_currency)
            chart_html = chart_fig.to_html(full_html=False)

            # Generate forecast chart
            forecast_df, forecast_fig = forecast(source_currency, dest_currency)
            forecast_html = forecast_fig.to_html(full_html=False)

        except Exception as e:
            # Log or handle errors specific to chart generation
            error = f"Error generating charts: {e}"

    # Get the list of currencies for the dropdowns
    df = etl_process()
    currencies = df["Currency"].unique()

    # Get top gainers and losers
    top_gain, top_loss = change_rate()

    # Render the template with context
    context = {
        "currencies": currencies,
        "converted_amount": converted_amount,
        "source_amount": source_amount,
        "source_currency": source_currency,
        "dest_currency": dest_currency,
        "error": error,
        "top_gain": top_gain.to_dict(orient="records"),
        "top_loss": top_loss.to_dict(orient="records"),
        "chart_html": chart_html,
        "forecast_html": forecast_html,
    }
    return render(request, "dashboard/dashboard.html", context)
