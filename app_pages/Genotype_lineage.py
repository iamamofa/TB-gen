import os
import base64
import streamlit as st
import numpy as np
import pandas as pd

from vcf import Reader
from gzip import open as gzopen
from collections import OrderedDict
from tempfile import NamedTemporaryFile
from annotated_text import annotated_text, annotation
from utils import set_page_config, sidebar_image, set_css

set_page_config()
sidebar_image()
set_css()

st.title("Genotype MTBC lineages from VCF file")

st.markdown("---")

annotated_text(
    "Use your own ",
    annotation(".VCF or .VCF.GZ", color="#525833", border="1px dashed"),
    " files as input to call lineage",
)

st.markdown(
    """
- Use can use both single- or multi-sample .VCF files
- Accepts multiple .VCF files at a time
- Variants should be called by mapping to [NC_000962.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000962.3/) _M. tuberculosis_ H37Rv genome
- Variants should be already filtered and contain only high quality calls
"""
)


levels_file = "./data/levels.txt"


@st.cache
def get_levels_dictionary(levels):

    temp_df = pd.read_csv(levels, sep="\t")
    uniqueLevels = temp_df["level"].unique()
    levelsDict = {elem: pd.DataFrame() for elem in uniqueLevels}

    for key in levelsDict.keys():
        levelsDict[key] = temp_df[:][temp_df["level"] == key]

    lvl1 = (
        levelsDict[1]["POS"].values,
        levelsDict[1]["REF"].values,
        levelsDict[1]["ALT"].values,
        levelsDict[1]["lineage"].values,
    )
    lvl2 = (
        levelsDict[2]["POS"].values,
        levelsDict[2]["REF"].values,
        levelsDict[2]["ALT"].values,
        levelsDict[2]["lineage"].values,
    )
    lvl3 = (
        levelsDict[3]["POS"].values,
        levelsDict[3]["REF"].values,
        levelsDict[3]["ALT"].values,
        levelsDict[3]["lineage"].values,
    )
    lvl4 = (
        levelsDict[4]["POS"].values,
        levelsDict[4]["REF"].values,
        levelsDict[4]["ALT"].values,
        levelsDict[4]["lineage"].values,
    )
    lvl5 = (
        levelsDict[5]["POS"].values,
        levelsDict[5]["REF"].values,
        levelsDict[5]["ALT"].values,
        levelsDict[5]["lineage"].values,
    )

    return lvl1, lvl2, lvl3, lvl4, lvl5


@st.cache
def get_levels_positions(levels):

    temp_df = pd.read_csv(levels, sep="\t")
    pos = temp_df["POS"].values
    return pos


@st.cache
def vcf_to_dataframe(vcf_file):

    pos_all = get_levels_positions(levels_file)
    vcf_reader = Reader(vcf_file, "r")
    res = []
    cols = ["Sample", "REF", "ALT", "POS"]

    for rec in vcf_reader:
        x = [rec.end]
        for sample in rec.samples:
            if sample.gt_bases == None:
                # no call
                row = [sample.sample, rec.REF, sample.gt_bases]
            elif rec.REF != sample.gt_bases:
                row = [sample.sample, rec.REF, sample.gt_bases] + x
            else:
                # call is REF
                row = [sample.sample, rec.REF, sample.gt_bases] + x

            res.append(row)

    res = pd.DataFrame(res, columns=cols)
    res = res[~res.POS.isnull()]

    res = res.astype(
        {"Sample": "object", "REF": "object", "ALT": "object", "POS": "int64"}
    )

    res = res.loc[res["POS"].isin(pos_all)]
    res = res.drop(res[res["REF"] == res["ALT"]].index)
    frames = [res]
    res = pd.concat(frames)
    res["ALT"] = res["ALT"].str.split("/").str.get(-1)
    return res


@st.cache
def lineage4_decision(call_list):

    lin4 = ["L4"]
    altList = []

    for item in call_list:
        if any(i in item for i in lin4):
            item = [x for x in item if x not in lin4]

        else:
            item.extend(["L4" for i in range(2)])

        altList.append(item)

    return altList


@st.cache
def lineage4_9_decision(call_list):

    lin4_9 = ["L4.9"]
    altList = []

    for item in call_list:
        if any(i in item for i in lin4_9):
            item = [x for x in item if x not in lin4_9]

        else:
            item.extend(["L4.9" for i in range(2)])

        altList.append(item)

    return altList


@st.cache
def count_level1_variants(call_list):

    d = OrderedDict()

    for item in call_list:
        if not len(item) == 0:
            caseless = item.casefold()
            try:
                d[caseless][1] += 1
            except KeyError:
                d[caseless] = [item, 1]

    call_list = []

    for item, count in d.values():
        if not item.startswith("L8"):
            if count > 1:
                item = "{}".format(item)
            elif count == 1:
                item = "{} [{}]".format(item, "warning! only 1/2 snp is present")
        call_list.append(item)

    return call_list


@st.cache
def count_level2_variants(call_list):

    d = OrderedDict()

    for item in call_list:
        if not len(item) == 0:
            caseless = item.casefold()
            try:
                d[caseless][1] += 1
            except KeyError:
                d[caseless] = [item, 1]

    call_list = []

    for item, count in d.values():
        if not item.startswith(("L2.2 (modern)", "L2.2 (ancient)")):
            if count > 1:
                item = "{}".format(item)
            elif count == 1:
                item = "{} [{}]".format(item, "warning! only 1/2 snp is present")
        elif item.startswith(("L2.2 (modern)", "L2.2 (ancient)")):
            if count > 1:
                item = "{}".format(item)
            elif count == 1:
                if not item.startswith("L2.2 (modern)"):
                    item = "{} [{}]".format(item, "warning! only 1/2 snp is present")
                if item.startswith("L2.2 (modern)"):
                    item = "{}".format(item)
        call_list.append(item)

    return call_list


@st.cache
def lineage2_decision(call_list):

    lin2 = ["L2.2 (modern)", "L2.2 (ancient)"]
    altList = []

    for item in call_list:
        if all(i in item for i in lin2) == True:
            item = list(set(item) - set(lin2))
            item.append("L2.2 (modern)")
        else:
            item = item

        altList.append(item)

    return altList


@st.cache
def convert_df_to_tsv(df):
    return df.to_csv(sep="\t", index=False).encode("utf-8")


@st.cache
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


@st.cache
def barcoding(uploaded_vcf):
    df = vcf_to_dataframe(uploaded_vcf)

    exp = (
        df["POS"].values[:, None],
        df["REF"].values[:, None],
        df["ALT"].values[:, None],
    )

    df["level_1"] = np.dot(
        np.logical_and.reduce(
            [
                np.equal(exp[0], lvl1[0]),
                np.equal(exp[1], lvl1[1]),
                np.equal(exp[2], lvl1[2]),
            ]
        ),
        lvl1[3],
    )

    df["level_2"] = np.dot(
        np.logical_and.reduce(
            [
                np.equal(exp[0], lvl2[0]),
                np.equal(exp[1], lvl2[1]),
                np.equal(exp[2], lvl2[2]),
            ]
        ),
        lvl2[3],
    )

    df["level_3"] = np.dot(
        np.logical_and.reduce(
            [
                np.equal(exp[0], lvl3[0]),
                np.equal(exp[1], lvl3[1]),
                np.equal(exp[2], lvl3[2]),
            ]
        ),
        lvl3[3],
    )

    df["level_4"] = np.dot(
        np.logical_and.reduce(
            [
                np.equal(exp[0], lvl4[0]),
                np.equal(exp[1], lvl4[1]),
                np.equal(exp[2], lvl4[2]),
            ]
        ),
        lvl4[3],
    )

    df["level_5"] = np.dot(
        np.logical_and.reduce(
            [
                np.equal(exp[0], lvl5[0]),
                np.equal(exp[1], lvl5[1]),
                np.equal(exp[2], lvl5[2]),
            ]
        ),
        lvl5[3],
    )

    df = df.drop(["REF", "ALT", "POS"], axis=1)
    df = df.replace("", np.nan)

    df = (
        df.groupby(["Sample"])
        .agg(lambda x: ",".join(x.dropna()))
        .reset_index()
        .reindex(columns=df.columns)
    )

    df2 = df.copy()

    df2["level_1"] = df2["level_1"].str.split(",")
    df2["level_2"] = df2["level_2"].str.split(",")
    df2["level_1"] = lineage4_decision(df2["level_1"])
    df2["level_2"] = lineage4_9_decision(df2["level_2"])
    df2["level_1"] = [count_level1_variants(item) for item in df2["level_1"]]
    df2["level_2"] = [count_level2_variants(item) for item in df2["level_2"]]
    df2["level_2"] = lineage2_decision(df2["level_2"])

    df2[["level_1", "level_2"]] = df2[["level_1", "level_2"]].applymap(
        lambda x: ", ".join(map(str, x))
    )

    df2 = df2.sort_values(
        by=["level_1", "level_2", "level_3", "level_4", "level_5"]
    ).reset_index(drop=True)

    return df2


def temporary_vcf_gz(uploaded_file):
    with NamedTemporaryFile(
        dir=".",
        suffix=".vcf.gz",
        delete=False,
    ) as temp_vcf:

        temp_vcf.write(uploaded_file.getbuffer())

    return temp_vcf.name


def temporary_vcf(uploaded_file):
    with NamedTemporaryFile(
        dir=".",
        suffix=".vcf",
        delete=False,
    ) as temp_vcf:

        temp_vcf.write(uploaded_file.getbuffer())

    return temp_vcf.name


@st.cache
def genotype_lineages(uploaded_file):
    uploaded_extension = uploaded_file.name.split(".")[-1]

    if uploaded_extension == "gz":
        try:
            temp_vcf = temporary_vcf_gz(uploaded_file)
            uploaded_vcf = gzopen(temp_vcf, "rt")
            result = barcoding(uploaded_vcf)
        finally:
            os.remove(temp_vcf)
    else:
        try:
            temp_vcf = temporary_vcf(uploaded_file)
            uploaded_vcf = open(temp_vcf)
            result = barcoding(uploaded_vcf)
        finally:
            os.remove(temp_vcf)
    return result


uploaded_files = st.sidebar.file_uploader(
    "Upload VCF file", type=["vcf", "vcf.gz"], accept_multiple_files=True
)


if st.sidebar.button("Genotype lineage"):
    if uploaded_files is not None:
        with st.spinner("Genotyping..."):

            try:
                lvl1, lvl2, lvl3, lvl4, lvl5 = get_levels_dictionary(levels_file)
                results_list = []

                for uploaded_file in uploaded_files:

                    out = genotype_lineages(uploaded_file)
                    results_list.append(out)
                results = pd.concat(results_list).reset_index(drop=True)

                st.dataframe(results, width=900)
                st.success("Done!", icon="✅")

                tsv = convert_df_to_tsv(results)
                csv = convert_df_to_csv(results)

                dwn1, dwn2, mock = st.columns([1, 1, 4])

                dwn1.download_button(
                    label="💾 Download data as TSV",
                    data=tsv,
                    file_name="lineage.tsv",
                    mime="text/csv",
                )

                dwn2.download_button(
                    label="💾 Download data as CSV",
                    data=csv,
                    file_name="lineage.csv",
                    mime="text/csv",
                )

            except ValueError:
                st.warning("No data was uploaded!", icon="⚠️")
            except StopIteration:
                st.error("VCF file is malformed!", icon="‼️")
    else:
        st.warning("No data was uploaded!", icon="⚠️")
else:
    st.info("Upload input data in the sidebar to start!", icon="👈")