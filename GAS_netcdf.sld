<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:sld="http://www.opengis.net/sld" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" version="1.0.0">  
    <sld:NamedLayer>
        <sld:Name>GAS_Netcdf</sld:Name>
        <sld:UserStyle>
            <sld:Name>GAS_Netcdf</sld:Name>
            <sld:Title>Simple test style for NETCDF</sld:Title>
            <sld:Abstract>Basic color Map</sld:Abstract>
            <sld:FeatureTypeStyle>
                <sld:Name>GAS_Netcdf</sld:Name>
                <sld:Rule>
                    <!-- <sld:Filter>
                        <sld:PropertyIsLessThan>
                            <sld:PropertyName>"${env('low',3)}"</sld:PropertyName>
                            <sld:Literal>100</sld:Literal>
                        </sld:PropertyIsLessThan>
                    </sld:Filter> -->
                    <sld:RasterSymbolizer>
                        <sld:ColorMap>
                            <sld:ColorMapEntry color="#000000" opacity="0.0" quantity="0.0" label="0.0"/>
                            <sld:ColorMapEntry color="#0000FF" quantity="${env('low',0.3)}" label="${env('low',0.3)}"/>
                            <!-- <sld:ColorMapEntry color="#007FFF" quantity="${env('medium_min',3)}" label="${env('medium_min',3)}"/> -->
                            <sld:ColorMapEntry color="#00FF00" quantity="${env('medium',30)}"  label="${env('medium',30)}"/>
                            <!-- <sld:ColorMapEntry color="#7FFF80" quantity="${env('medium_max',300)}"  label="${env('medium_max',300)}"/> -->
                            <sld:ColorMapEntry color="#FF0000" quantity="${env('high',300)}"  label="${env('high',300)}"/>
                        </sld:ColorMap>
                        <sld:ContrastEnhancement/>
                    </sld:RasterSymbolizer>
                </sld:Rule>
            </sld:FeatureTypeStyle>
        </sld:UserStyle>
    </sld:NamedLayer>
</sld:StyledLayerDescriptor>