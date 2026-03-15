import contextlib
import io
import time
import uuid
import boto3
from strands import tool
from config.settings import S3_FOLDER
import matplotlib
import matplotlib.pyplot as plt
from strands.agent import Agent



@tool(
    name="visual_generator",
    description=(
        "When the user requests a chart, graph, or visualization — or when you determine that a visual explanation "
        "would be helpful — follow these steps:\n"
        "### Chart generation rules:\n"
        "- Generate valid Python code using matplotlib. Always include `import matplotlib.pyplot as plt`.\n"
        "- Begin each figure using `fig, ax = plt.subplots(...)` (or `fig, axes = plt.subplots(...)` for multiple "
        "panels) with an explicit `figsize` (e.g. `(16, 10)`). Do not call `plt.figure(...)` separately.\n"
        "- Only one figure per `visual_generator` invocation — even if the user requests multiple charts. Use "
        "subplots inside that figure for dashboards.\n"
        "- The chart must be meaningful — do not generate empty or placeholder visuals. It must contain real data and "
        "visible elements.\n"
        "- If insufficient data is available, do not fabricate values. Instead, explain that the chart cannot be "
        "generated due to missing data.\n"
        "### Layout rules to avoid overlap (critical):\n"
        "- For dashboards with multiple charts/tables, always use "
        "`fig, axes = plt.subplots(nrows=..., ncols=..., figsize=(16, 10), constrained_layout=False)` or "
        "`matplotlib.gridspec.GridSpec`. Do not use hard-coded `fig.add_axes([...])` coordinates.\n"
        "- Use a figure-level title with extra top margin, for example: "
        "`fig.suptitle('TITLE', fontsize=16, y=0.97)`.\n"
        "- After all plotting is done, adjust layout to prevent overlap using either "
        "`fig.tight_layout(pad=2.0, rect=[0.02, 0.02, 0.98, 0.90])` or "
        "`plt.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.08, wspace=0.35, hspace=0.45)`.\n"
        "- For bar charts with value labels on bars, use padding and smaller text so labels don’t sit on or outside "
        "the bars, e.g. `ax.bar_label(bars, padding=4, fontsize=8)`.\n"
        "- For charts with many x-axis categories or long tick labels, rotate and/or thin them so they do not "
        "overlap, e.g. `plt.xticks(rotation=45, ha='right')` and optionally label every nth tick.\n"
        "- For tables created with `ax.table(...)`, always:\n"
        "  - Pass `colWidths` sized to fit the figure (e.g. `colWidths=[1.0 / ncols] * ncols`).\n"
        "  - Use short header text or line breaks (`'\\n'`) instead of long single-line headers.\n"
        "  - Set a small font size (e.g. disable auto size and use font size 8).\n"
        "  - Call `table.scale(x_scale, y_scale)` if needed to keep text inside cells.\n"
        "  - Place tables in their own subplot (for example, a dedicated row in `GridSpec`) so they don’t overlap "
        "other charts.\n"
        "### General rules:\n"
        "- Prevent image cutoff: ensure that all axis labels, ticks, titles, data, legends, and table text are fully "
        "visible after layout adjustment.\n"
        "- Set clear titles, axis labels, legends, and annotations, but avoid clutter that would cause text to "
        "collide.\n"
        "- Do not include `plt.savefig(...)` in the code.\n"
        "- Pass the full matplotlib code as the `code` string argument to this `visual_generator` tool — do not "
        "execute the plotting code inline.\n"
        "- Do not add any S3 URLs or image URLs returned by this tool inside the final natural-language response.\n"
        "- Limit to 3 visualizations per session. If the user requests more, respond politely in text that only up to "
        "3 charts can be generated per session and skip additional chart generation.\n"
    ),
)
def visual_generator(agent:Agent,code: str) -> str:
    """
    Executes a block of Python code and captures stdout.
    Saves matplotlib figures as PNG files if they exist.
    """
    output = io.StringIO()
    image_paths = []
    s3_bucket_region = agent.state.get("s3_bucket_region")
    s3_bucket_name = agent.state.get("s3_bucket_name")

    print(f"using visual output tool s3 bucket region : {s3_bucket_region}, s3 bucket name ;{s3_bucket_name}")

    # Create an S3 client
    s3 = boto3.client("s3", region_name=s3_bucket_region)

    try:
        matplotlib.use("Agg")

        # Get initial figure numbers
        initial_fignums = set(plt.get_fignums())

        # Redirect stdout
        with contextlib.redirect_stdout(output):
            # Safe isolated execution
            exec_globals = {"__name__": "__main__"}
            exec(code, exec_globals)

        # Get only NEW figures created by this execution
        new_fignums = set(plt.get_fignums()) - initial_fignums

        # Save all open figures
        figures = [plt.figure(n) for n in new_fignums]

        # Saving Files in the local system.
        # for fig in figures:
        #     filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        #     filepath = os.path.join(os.getcwd(), "output", filename)
        #     os.makedirs(os.path.dirname(filepath), exist_ok=True)
        #     fig.savefig(filepath)
        #     image_paths.append(filepath)

        # Uploading File to S3
        for fig in figures:

            if not fig.axes:
                continue

            buffer = io.BytesIO()
            fig.savefig(buffer, format='png')
            buffer.seek(0)

            random_hex = uuid.uuid4().hex
            epoch_time = int(time.time())

            filename: str = f"{S3_FOLDER}chart_{epoch_time}_{random_hex}.png"
            s3.upload_fileobj(buffer, s3_bucket_name, filename, ExtraArgs={'ContentType': 'image/png'})

            image_url: str = f"https://{s3_bucket_name}.s3.{s3_bucket_region}.amazonaws.com/{filename}"

            if image_url:
                print(f"Printing image url from visual generator tool: {image_url}")
                image_paths.append(image_url)
                print("Received image url:", image_paths)

        # Accumulate image URLs from all tool calls in the agent state
        all_images = agent.state.get("visual_output") or []
        all_images.extend(image_paths)
        agent.state.set("visual_output", all_images)


        return "Image generated successfully"
    except Exception as e:
        return f"[ERROR] {str(e)}"