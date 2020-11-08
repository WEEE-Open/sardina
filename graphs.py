import matplotlib.pyplot as plot
from typing import List

class Graph:
    def __init__(self,
                 data: list = [],
                 minimum: int = 0,
                 min_count: int = 0,
                 kind: str = 'pie',
                 legend: str = 'Default graph legend',
                 title: str = 'Default graph title',
                 counter: str = 'total'):

        self.minimum = minimum
        self.min_count = min_count
        self.kind = kind
        self.legend = legend
        self.title = title
        self.counter = counter

        # Graph generation code expects a list but callers might specify a single list if they only need one dataset.
        if isinstance(data, dict):
            self.data = [data]
        else:
            self.data = data

        # Normalize and count the elements
        self.normalize_data()

        self.count = []
        for dataset in self.data:
            self.count.append(len(dataset))

    def normalize_data(self):
        result = []

        for i,dataset in enumerate(self.data):
            ds = dict(self.data[i])

            # Remove summatory keys from the dictionary.
            # The additional 'nope' is there just to avoid having to put everything in a try in case the "total" key does not exist. 
            ds.pop('total', 'nope')
            ds.pop('past_year', 'nope')

            other = 0

            for key in list(ds.keys()):
                if ds[key] < self.minimum:
                    other += ds.pop(key)

            # Order data dictionary by size of elements
            ds = {k:v for k,v in sorted(ds.items(), key=lambda x: int(x[1]), reverse=True)}

            if other > 0:
                ds['other'] = other

            result.append(ds)

        self.data = result

    def is_suitable(self) -> bool:
        for c in self.count:
            if c > 0:
                return True
        
        return False


def generate_figure(graphs: List[Graph], path: str):
    filtered = sorted([graph for graph in graphs if graph.is_suitable()], key=lambda x: 0 if x.kind == 'pie' else 1)
    heights = []

    # If we have no suitable graphs, return without doing nothing
    if len(filtered) == 0:
        return

    for graph in filtered:
        if graph.kind == 'pie':
            heights.append(7)
        else:
            heights.append((0.3 * max(graph.count)))

    figure, axis = plot.subplots(len(filtered),
                                 figsize=(12, sum(heights) + 2.5),
                                 dpi=600,
                                 gridspec_kw={'height_ratios': [h / heights[0] for h in heights]})

    # We need a list for the following for loop and if len(filtered) = 1 axis is just an object. Maybe there is a better way to do this?
    if len(filtered) == 1:
        axis = [axis]

    for i,graph in enumerate(filtered):
        generate_chart(graph.data, graph.minimum, graph.kind, graph.legend, graph.counter, graph.title, axis[i])
    
    plot.tight_layout()
    plot.savefig(path, bbox_inches='tight')
    plot.close(figure)


def generate_chart(data: list, minimum: int, graph_type: str, legend: str, counter: str, title: str, axis):
    keys    = [dataset.keys() for dataset in data]
    values  = [dataset.values() for dataset in data]
    counts  = [len(v) for v in values]
    totals  = [sum(dataset[key] for key in dataset) for dataset in data]
    classes = [len(dataset) if counter == 'classes' else totals[i] for i,dataset in enumerate(data)]
    labels  = [(f'{key} ({((dataset[key] * 100)/totals[i]):.2f}%)' for key in dataset) for i,dataset in enumerate(data)]

    for i,dataset in enumerate(data):
        if len(dataset) == 0:
            continue

        if graph_type == 'pie':
            # Set the color map and generate a properly sized color cycle
            colors = []
            colormaps = {'Pastel1':9, 'Accent':8, 'Set1':9, 'tab20':20, 'tab20b':20}

            for colormap in colormaps:
                cmap = plot.get_cmap(colormap)
                colors += [cmap(i/colormaps[colormap]) for i in range(colormaps[colormap])]

            step = int(len(colors)/counts[i])
            axis.set_prop_cycle('color', [colors[i*step] for i in range(counts[i])])

            wedges, texts = axis.pie(values[i], counterclock=False, startangle=90)
            legend = axis.legend(wedges, labels[i], title=legend, bbox_to_anchor=(1.01, 1), loc='upper left')
            axis.set_aspect('equal')
            axis.set_title(f'{title} (total: {classes[i]})')

        elif graph_type == 'bar':
            if len(data) == 1:
                colors = ['C0']
            else:
                colors = ['C2', 'C3']

            y = [i for i in range(counts[i])]

            bars = axis.barh(y, values[i], align='center', color=colors[i])
            axis.set_yticks(y)
            axis.set_yticklabels(keys[i])
            axis.invert_yaxis()
            axis.set_xlabel(legend)
            axis.set_title(f'{title} (total: {classes[i]})')

            for bar in bars:
                width = bar.get_width()
                axis.annotate(str(width), xy=(width, bar.get_y() + bar.get_height() / 2), xytext=(3,0), textcoords='offset points', ha='left', va='center')