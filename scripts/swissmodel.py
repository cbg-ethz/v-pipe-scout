import gzip
import io
import matplotlib.pyplot as plt
import matplotlib as mpl
import codecs
import urllib.parse

def generate_swissmodel_link(protein_name, variant_list, colormap_name='rainbow'):
    """Generate link to SWISS-MODEL visualization.
    For now, we implement this in Python instead of Javascript,
    because the required data transformations (gzip, base64-encode, url-encode)
    are more asily implemented that way.
    Docs:
        * https://swissmodel.expasy.org/docs/repository_help#smr_parameters
        * https://swissmodel.expasy.org/repository/user_annotation_upload
        * https://matplotlib.org/3.3.2/tutorials/colors/colormaps.html
    """
    # convert variant list to string representation
    reference = 'https://github.com/cbg-ethz/V-pipe'
    color_map = plt.cm.get_cmap(colormap_name, len(variant_list))

    string_content = ''
    for i, entry in enumerate(variant_list):
        start_pos, end_pos, annotation = entry
        color = mpl.colors.to_hex(color_map(i))

        string_content += f'{protein_name} {start_pos} {end_pos} {color} {reference} {annotation}\n'

    # transform string to required format
    bytes_content = string_content.encode()

    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='w', compresslevel=9) as fd:
        fd.write(bytes_content)
    zlib_content = out.getvalue()

    base64_content = codecs.encode(zlib_content, 'base64')
    urlquoted_content = urllib.parse.quote(base64_content.rstrip(b'\n'))

    # embed in URL
    base_url = 'https://swissmodel.expasy.org/repository/uniprot/{protein_name}?annot={query}'

    return base_url.format(protein_name=protein_name, query=urlquoted_content)


if __name__ == '__main__':

    protein_name = 'P0DTC2'  # SARS-CoV-2 spike protein
    variant_list = ["S:P337H",
                    "S:P337L",
                    "S:P337R",
                    "S:P337S",
                    "S:P337T",
                    "S:E340A",
                    "S:E340D",
                    "S:E340G",
                    "S:E340K",
                    "S:E340Q",
                    "S:E340V",
                    "S:T345P",
                    "S:R346G",
                    "S:R346I"
                    ]

    # convert to required format
    formatted_variant_list = []
    for var in variant_list:
        var = var.lstrip('S:')  # remove prefix
        aa, pos = var[0], var[1:-1]
        pos = int(pos)
        formatted_variant_list.append((pos, pos, var))  
    
    print(variant_list)

    link = generate_swissmodel_link(protein_name, formatted_variant_list, colormap_name='rainbow')

    print(link)
    